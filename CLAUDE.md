# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This is a multi-package monorepo. The user-facing package is `packages/markitdown`; the other three are distributed separately and live alongside it.

| Package | Purpose |
|---|---|
| `packages/markitdown` | Core library + CLI (`markitdown` command). Build/test focus. |
| `packages/markitdown-mcp` | MCP server exposing MarkItDown as a tool. |
| `packages/markitdown-ocr` | Plugin adding LLM-Vision OCR to PDF/DOCX/PPTX/XLSX converters. |
| `packages/markitdown-sample-plugin` | Reference implementation for 3rd-party plugin authors. |

All packages are independent Python projects (each with its own `pyproject.toml`).

## Build, test, and lint

The core package uses **hatch** as build/test runner and **pre-commit** (black formatter) for linting. From repo root:

```sh
# Install hatch
pip install hatch

# Enter the hatch env (installs [all] extras from pyproject.toml)
cd packages/markitdown
hatch shell

# Run the full test suite
hatch test

# Run a single test (hatch test forwards args to pytest)
hatch test -k test_module_vectors
hatch test tests/test_pdf_memory.py::test_foo

# Type-check (mypy, with --ignore-missing-imports)
hatch run types:check

# Format / lint
pre-commit run --all-files   # runs black via .pre-commit-config.yaml at repo root
```

CI (`.github/workflows/tests.yml`) runs `hatch test` on Python 3.10 / 3.11 / 3.12 and pre-commit on every PR. Hatch is installed via `pipx` in CI, not `pip`.

The devcontainer (`.devcontainer/`) has all deps pre-installed — `hatch test` works there without further setup.

## Architecture

### Public API surface

`packages/markitdown/src/markitdown/__init__.py` exports exactly the symbols callers should use: `MarkItDown`, `DocumentConverter`, `DocumentConverterResult`, `StreamInfo`, the exception hierarchy, and two priority constants. Anything not re-exported here is considered private (leading underscore).

### Conversion pipeline (`_markitdown.py`)

`MarkItDown.convert(source, ...)` is a smart router that dispatches to one of four entry points based on input type:

- `str` starting with `http://`, `https://`, `file:`, `data:` → `convert_uri`
- `str` / `Path` otherwise → `convert_local`
- `requests.Response` → `convert_response`
- file-like object with `.read()` → `convert_stream`

All four ultimately call the private `_convert()`, which iterates the **registered converters in priority order** (lowest priority value first; stable sort so registration order is the tiebreaker). For each converter it:

1. Calls `accepts(file_stream, stream_info, **kwargs)` — must be cheap, **must not advance `file_stream.tell()`** (the position is asserted between calls).
2. If accepted, calls `convert(...)` in a `try/except` that resets the stream position to the original on failure.
3. Collects failures into a `FailedConversionAttempt` list; raises `FileConversionException` only after every converter has had a chance.

The final result is normalized: trailing whitespace per line stripped, runs of 3+ blank lines collapsed to 2.

### Stream-info guessing (`_get_stream_info_guesses`)

Before iteration, `_convert` builds a list of `StreamInfo` candidates — typically the user-supplied hint plus a **Magika** content-detection pass. The magika result is cross-checked against the base guess for compatibility (mimetype, extension, charset); if compatible they're merged, otherwise both are tried independently. An empty `StreamInfo()` is always tried last as a final fallback.

### Converter priorities

Two constants in `_markitdown.py`:

- `PRIORITY_SPECIFIC_FILE_FORMAT = 0.0` — format-specific (PDF, DOCX, XLSX, etc.)
- `PRIORITY_GENERIC_FILE_FORMAT = 10.0` — catch-alls (`text/*`, ZIP, HTML)

Lower values are tried first, so **specific converters are tried before generic ones**. The built-in registration order in `enable_builtins()` matters: generic converters are registered first (lower priority) so they end up *last* in the iteration. The cloud converters (`DocumentIntelligenceConverter`, `ContentUnderstandingConverter`) are inserted at the top of the stack only when the corresponding endpoint kwarg is supplied at construction.

Plugins can register at any priority. A plugin with priority `9` runs after all built-in specifics but before the built-in generics.

### Plugin system

Plugins are discovered via `importlib.metadata` entry points in the `markitdown.plugin` group. Each entry point must export a module with a `register_converters(markitdown: MarkItDown, **kwargs)` function. See `packages/markitdown-sample-plugin/src/markitdown_sample_plugin/_plugin.py` for the canonical example (declares `__plugin_interface_version__`, `ACCEPTED_MIME_TYPE_PREFIXES`, `ACCEPTED_FILE_EXTENSIONS`).

Plugins are **off by default**; activate with `MarkItDown(enable_plugins=True)` or `--use-plugins` on the CLI.

### Converter contract (`_base_converter.py`)

Every converter subclasses `DocumentConverter` and implements two methods:

- `accepts(file_stream, stream_info, **kwargs) -> bool` — may peek at the stream (e.g. `OutlookMsgConverter` does) but **must `seek()` back** before returning.
- `convert(file_stream, stream_info, **kwargs) -> DocumentConverterResult` — returns `{markdown: str, title: str | None}`. The `text_content` property on the result is a soft-deprecated alias for `markdown`.

The `_kwargs` passed to both include the LLM client/model/prompt and `_parent_converters` (used for nested conversions, e.g. ZIP iterating into child files via `convert_stream`).

### Optional dependencies and cloud converters

`pyproject.toml` defines extras (`[pdf]`, `[docx]`, `[pptx]`, `[xlsx]`, `[xls]`, `[outlook]`, `[az-doc-intel]`, `[az-content-understanding]`, `[audio-transcription]`, `[youtube-transcription]`, plus `[all]`). Cloud converters require their extra plus runtime credentials:

- `MarkItDown(docintel_endpoint=...)` activates `DocumentIntelligenceConverter` and optionally accepts `docintel_credential`, `docintel_file_types`, `docintel_api_version`.
- `MarkItDown(cu_endpoint=...)` activates `ContentUnderstandingConverter` and accepts `cu_credential`, `cu_analyzer_id`, `cu_file_types` (list of `ContentUnderstandingFileType`). Each `convert()` call routed to CU is a billable Azure call — use `cu_file_types` to restrict routing.

### LLM integration for image/PDF descriptions

Image, PPTX, and PDF converters call out to an OpenAI-compatible client when `MarkItDown(llm_client=..., llm_model=..., llm_prompt=...)` is provided. The client is also passed to plugin converters (e.g. `markitdown-ocr`) via the same kwargs — this is the seam for vision-based OCR.

## Security posture

The README's `Security Considerations` section is non-negotiable. `MarkItDown.convert()` is **permissive** (accepts paths, URIs, response objects) and runs with the calling process's privileges. In any untrusted-input or server-side context:

- Sanitize inputs before calling MarkItDown.
- Use the **narrowest** entry point that fits: `convert_local()` for local files, `convert_response()` after fetching with your own `requests.get()`, `convert_stream()` for byte streams. Do not call `convert()` on user-supplied strings.
- The `file:` URI scheme is restricted to empty netloc / `localhost` in `convert_uri`.

Do not weaken these guards.

## CLI surface (`__main__.py`)

`markitdown <filename>` reads from stdin if no filename. Key flags: `-o` (output file), `-x/-m/-c` (extension/mimetype/charset hints for stdin), `-d -e <endpoint>` (Document Intelligence), `--use-cu --cu-endpoint <endpoint>` (Content Understanding), `--cu-analyzer` / `--cu-file-types` for CU configuration, `-p/--use-plugins`, `--list-plugins`, `--keep-data-uris` (default: data URIs are truncated).

## Things to know before editing

- The CI test step pins `actions/checkout@v5` and `actions/setup-python@v5`. New Python versions in `tests.yml` are tested on every PR.
- `py.typed` is shipped (the package is PEP 561 compliant).
- Coverage is configured (`coverage.run` parallel mode, `coverage.paths` for src-layout). Tests emit `.coverage` artifacts; CI does not enforce a minimum coverage gate, but locally `coverage combine && coverage report` works after a parallel `hatch test`.
- The Python minimum is **3.10**; do not use 3.11+-only syntax in core code.
- The package is published as `markitdown` on PyPI; bumping `__version__` in `packages/markitdown/src/markitdown/__about__.py` is the release step (dynamic version in `pyproject.toml` reads from there).

@echo off
REM Development launcher for MarkItDown GUI on Windows.
REM Runs the Flet app from source, with hot-reload-friendly entry point.

setlocal
cd /d "%~dp0\.."

REM In monorepo dev: install sibling markitdown from local source first
REM (overrides any PyPI version) so GUI picks up local changes.
if exist "..\markitdown\pyproject.toml" (
    echo [markitdown-gui] Installing sibling markitdown[all] from local source...
    pip install -e "..\markitdown[all]"
)

echo [markitdown-gui] Installing package in editable mode (dev deps)...
pip install -e ".[dev]"

echo [markitdown-gui] Starting app...
python -m markitdown_gui %*

endlocal

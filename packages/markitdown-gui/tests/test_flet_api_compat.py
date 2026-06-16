"""Static-compatibility check for Flet's runtime API.

Flet 0.28's `Colors` and `Icons` enums are subsets of the full Material 3
spec. When we upgrade Flet (or develop on a slightly different patch
version), references like `ft.Colors.SURFACE_VARIANT` may suddenly
`AttributeError` at runtime. This test walks our source tree, collects
every `ft.Colors.XXX` / `ft.Icons.XXX` reference, and asserts each name
exists on the installed Flet. Cheap insurance against silent breakage.

Also scans for Flet control constructor calls (e.g. `ft.TextField(...)`)
and asserts that every keyword argument we pass exists in the
corresponding Flet class's `__init__` signature. Catches
`placeholder=` (Flutter name) vs `hint_text=` (Flet name) and similar
mistakes without us having to actually launch the app.

Skipped automatically if Flet isn't installed in the test env.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

# Skip the whole module if Flet isn't importable (e.g. minimal CI env).
pytest.importorskip("flet")

import flet as ft  # type: ignore[import-not-found]


SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "markitdown_gui"

_COLORS_RE = re.compile(r"ft\.Colors\.([A-Z_][A-Z_0-9]*)")
_ICONS_RE = re.compile(r"ft\.Icons\.([A-Z][A-Z_0-9]*)")


def _scan_source(pattern: re.Pattern[str]) -> set[str]:
    found: set[str] = set()
    for path in SRC_ROOT.rglob("*.py"):
        if not path.is_file():
            continue
        for m in pattern.finditer(path.read_text(encoding="utf-8")):
            found.add(m.group(1))
    return found


# --- Enum-name checks (Colors, Icons) -----------------------------------


def test_all_color_refs_exist() -> None:
    from flet.core.colors import Colors

    refs = _scan_source(_COLORS_RE)
    missing = sorted(c for c in refs if not hasattr(Colors, c))
    assert not missing, (
        f"These ft.Colors.* names are referenced in our source but missing "
        f"from installed Flet: {missing}"
    )


def test_all_icon_refs_exist() -> None:
    from flet.core.icons import Icons

    refs = _scan_source(_ICONS_RE)
    missing = sorted(c for c in refs if not hasattr(Icons, c))
    assert not missing, (
        f"These ft.Icons.* names are referenced in our source but missing "
        f"from installed Flet: {missing}"
    )


# --- Constructor kwarg checks -------------------------------------------


def _scan_kwargs() -> list[tuple[Path, int, str, str, str]]:
    """Return (path, line, control_name, kwarg_name, value_repr) for every
    `ft.SomeControl(..., kwarg=..., ...)` call in our source."""
    results: list[tuple[Path, int, str, str, str]] = []
    for path in SRC_ROOT.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # Match `ft.Foo(...)` where Foo is the control name.
            func = node.func
            control_name: str | None = None
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id == "ft":
                    control_name = func.attr
            if control_name is None:
                continue
            for kw in node.keywords:
                if kw.arg is None:  # **kwargs spread — skip
                    continue
                try:
                    value_repr = ast.unparse(kw.value)
                except Exception:
                    value_repr = "?"
                results.append((path, node.lineno, control_name, kw.arg, value_repr))
    return results


def test_all_flet_kwargs_exist() -> None:
    """Every `ft.XControl(kwarg=...)` call must use kwargs accepted by
    Flet's `XControl.__init__`."""
    refs = _scan_kwargs()
    bad: list[tuple[Path, int, str, str]] = []
    for path, line, control_name, kwarg, _ in refs:
        cls = getattr(ft, control_name, None)
        if cls is None:
            # Not a Flet control we recognize (could be a local class).
            # The enum-name tests already cover known Flet names.
            continue
        try:
            sig = inspect.signature(cls.__init__)
        except (TypeError, ValueError):
            continue
        if kwarg in sig.parameters:
            continue
        # `**kwargs` (VAR_KEYWORD) accepts anything — pass.
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            continue
        bad.append((path, line, control_name, kwarg))

    if bad:
        lines = "\n".join(f"  {p}:{ln}  {ctrl}({kw}=...)" for p, ln, ctrl, kw in bad)
        pytest.fail(
            "These ft.*() constructor calls use kwargs that don't exist on "
            "the installed Flet (likely Flutter-vs-Flet naming drift):\n"
            + lines
        )

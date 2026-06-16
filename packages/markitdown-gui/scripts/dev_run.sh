#!/usr/bin/env bash
# Development launcher for MarkItDown GUI on macOS / Linux.
# Runs the Flet app from source.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# In monorepo dev: install sibling markitdown from local source first
# (overrides any PyPI version) so GUI picks up local changes.
if [ -f "../markitdown/pyproject.toml" ]; then
    echo "[markitdown-gui] Installing sibling markitdown[all] from local source..."
    pip install -e "../markitdown[all]"
fi

echo "[markitdown-gui] Installing package in editable mode (dev deps)..."
pip install -e ".[dev]"

echo "[markitdown-gui] Starting app..."
python -m markitdown_gui "$@"

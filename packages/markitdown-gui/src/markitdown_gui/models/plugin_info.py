"""Plugin metadata for the Plugins view."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PluginInfo:
    """A discoverable markitdown plugin (from entry_points group 'markitdown.plugin')."""

    name: str  # entry point name, e.g. "ocr"
    module: str  # top-level module name, e.g. "markitdown_ocr"
    version: str  # "unknown" if not discoverable
    distribution: str  # "markitdown-ocr" — the pip package it came from
    loaded: bool  # True if it imported successfully when MarkItDown was constructed
    enabled: bool  # current user setting

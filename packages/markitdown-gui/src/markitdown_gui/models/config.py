"""Non-secret application configuration, persisted as JSON.

API keys (openai_api_key, docintel_key, cu_key) live in the OS keyring
via SettingsService, NOT in this dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class AppConfig:
    """User-tunable settings that are safe to store in plain text."""

    # --- LLM (image description / OCR) ---
    openai_base_url: str | None = None
    openai_model: str | None = None

    # --- Document Intelligence ---
    docintel_endpoint: str | None = None
    docintel_api_version: str | None = None

    # --- Content Understanding ---
    cu_endpoint: str | None = None
    cu_analyzer_id: str | None = None
    cu_file_types: list[str] = field(default_factory=list)

    # --- Output ---
    default_output_dir: str | None = None  # None = same dir as source file
    keep_data_uris: bool = False

    # --- Plugin allowlist (empty = all loaded plugins enabled) ---
    enabled_plugins: list[str] = field(default_factory=list)

    # --- Advanced (rarely touched) ---
    exiftool_path: str | None = None
    style_map: str | None = None

    # --- Internal: keyring availability flag (not user-editable) ---
    keyring_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Build an AppConfig from arbitrary JSON, ignoring unknown keys."""
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

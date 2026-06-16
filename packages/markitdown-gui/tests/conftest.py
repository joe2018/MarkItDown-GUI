"""Shared pytest fixtures.

Forces every test to use a fresh, isolated user-data directory under
`tmp_path` so we never touch the developer's real MarkItDown config.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_user_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all platformdirs lookups to a temp dir for the test."""
    # platformdirs reads XDG_DATA_HOME / APPDATA on first call, then caches;
    # re-importing the module per test would be heavy. Instead, we override
    # the module-level user_data_dir function via monkeypatch.
    from markitdown_gui.services import paths_service

    fake = tmp_path / "userdata"
    fake.mkdir(parents=True, exist_ok=True)

    def _patched_user_data_dir(*args: object, **kwargs: object) -> str:
        return str(fake)

    monkeypatch.setattr(paths_service, "user_data_dir", _patched_user_data_dir)
    return fake


@pytest.fixture
def settings_service(isolated_user_data_dir: Path):
    """A fresh SettingsService bound to the temp data dir."""
    from markitdown_gui.services.settings_service import SettingsService

    return SettingsService()

"""Tests for SettingsService.

These tests run against the real OS keyring. On CI this is usually the
macOS Keychain on macOS, Credential Manager on Windows, or the Secret
Service on Linux. The `isolated_user_data_dir` fixture (see conftest.py)
keeps our config JSON in tmp; the keyring is shared but we use unique
service+key combinations and clean up after ourselves.
"""

from __future__ import annotations

import json
from pathlib import Path

import keyring
import keyring.errors
import pytest

from markitdown_gui.models.config import AppConfig
from markitdown_gui.services.settings_service import (
    KEYRING_SERVICE,
    SECRET_FIELDS,
    SettingsService,
)


# --- Config I/O ------------------------------------------------------------


def test_default_config_is_empty(settings_service: SettingsService) -> None:
    cfg = settings_service.get_config()
    assert cfg.openai_base_url is None
    assert cfg.openai_model is None
    assert cfg.docintel_endpoint is None
    assert cfg.cu_endpoint is None
    assert cfg.cu_file_types == []
    assert cfg.enabled_plugins == []
    assert cfg.keep_data_uris is False
    assert cfg.default_output_dir is None


def test_save_and_reload_config(
    settings_service: SettingsService, isolated_user_data_dir: Path
) -> None:
    cfg = AppConfig(
        openai_base_url="https://api.example.com/v1",
        openai_model="gpt-4o",
        docintel_endpoint="https://docintel.example.com",
        cu_file_types=["pdf", "jpeg"],
        enabled_plugins=["markitdown_ocr"],
        keep_data_uris=True,
    )
    settings_service.save_config(cfg)
    assert (isolated_user_data_dir / "config" / "config.json").exists()

    # Read raw JSON and assert fields are there
    raw = json.loads((isolated_user_data_dir / "config" / "config.json").read_text())
    assert raw["openai_base_url"] == "https://api.example.com/v1"
    assert raw["cu_file_types"] == ["pdf", "jpeg"]

    # Reload via a fresh service
    fresh = SettingsService()
    loaded = fresh.get_config()
    assert loaded.openai_model == "gpt-4o"
    assert loaded.cu_file_types == ["pdf", "jpeg"]
    assert loaded.keep_data_uris is True


def test_save_config_is_atomic(
    settings_service: SettingsService, isolated_user_data_dir: Path
) -> None:
    """No .tmp file should be left behind after save."""
    settings_service.save_config(AppConfig(openai_model="m"))
    tmp = isolated_user_data_dir / "config" / "config.json.tmp"
    assert not tmp.exists()


def test_corrupt_config_falls_back_to_default(
    settings_service: SettingsService, isolated_user_data_dir: Path
) -> None:
    config_path = isolated_user_data_dir / "config" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{not valid json", encoding="utf-8")
    fresh = SettingsService()
    assert fresh.get_config().openai_model is None


# --- Secret I/O ------------------------------------------------------------


@pytest.mark.parametrize("field_name", SECRET_FIELDS)
def test_secret_round_trip(
    settings_service: SettingsService, field_name: str
) -> None:
    if not settings_service._keyring_ok:  # noqa: SLF001 — test internals
        pytest.skip("Keyring unavailable in this environment")
    try:
        settings_service.set_secret(field_name, "value-for-" + field_name)
        assert settings_service.get_secret(field_name) == "value-for-" + field_name
    finally:
        settings_service.delete_secret(field_name)
        assert settings_service.get_secret(field_name) is None


def test_set_secret_rejects_unknown_field(settings_service: SettingsService) -> None:
    with pytest.raises(ValueError, match="Unknown secret field"):
        settings_service.set_secret("not_a_real_field", "x")


def test_get_secret_rejects_unknown_field(settings_service: SettingsService) -> None:
    with pytest.raises(ValueError, match="Unknown secret field"):
        settings_service.get_secret("not_a_real_field")


def test_delete_secret_rejects_unknown_field(settings_service: SettingsService) -> None:
    with pytest.raises(ValueError, match="Unknown secret field"):
        settings_service.delete_secret("not_a_real_field")


# --- build_markitdown ------------------------------------------------------


def test_build_markitdown_returns_instance(settings_service: SettingsService) -> None:
    """build_markitdown must always return a usable MarkItDown, even with
    no config (defaults: builtins enabled, plugins disabled)."""
    from markitdown import MarkItDown

    md = settings_service.build_markitdown()
    assert isinstance(md, MarkItDown)


def test_build_markitdown_does_not_explode_with_partial_config(
    settings_service: SettingsService,
) -> None:
    """If user filled endpoint but not key, we should still return a working
    MarkItDown (the cloud converter just won't be registered)."""
    settings_service.save_config(
        AppConfig(
            docintel_endpoint="https://example.com",
            # docintel_key intentionally absent
        )
    )
    md = settings_service.build_markitdown()
    assert md is not None

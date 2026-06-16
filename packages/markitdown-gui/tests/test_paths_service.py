"""Tests for paths_service."""

from __future__ import annotations

from pathlib import Path

from markitdown_gui.services import paths_service


def test_user_data_path_is_created(tmp_path: Path) -> None:
    p = paths_service.user_data_path()
    assert p.exists()
    assert p.is_dir()


def test_config_dir_is_created() -> None:
    p = paths_service.config_dir()
    assert p.exists()
    assert p.is_dir()
    assert (paths_service.user_data_path() / "config") == p


def test_config_file_is_under_config_dir() -> None:
    cfg = paths_service.config_file()
    assert cfg.parent == paths_service.config_dir()
    assert cfg.name == "config.json"


def test_logs_dir_returns_a_directory() -> None:
    p = paths_service.logs_dir()
    assert p.exists()
    assert p.is_dir()


def test_fallback_secrets_file_is_under_config_dir() -> None:
    p = paths_service.fallback_secrets_file()
    assert p.parent == paths_service.config_dir()
    assert p.name == "secrets.enc.json"

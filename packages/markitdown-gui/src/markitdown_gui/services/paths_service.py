"""User-data directory paths via platformdirs.

Centralizes where config files, logs, and cached assets live so the rest
of the app never hardcodes paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir, user_log_dir


# App identity used by platformdirs. Second arg is the "appauthor" component
# on Windows; harmless on macOS / Linux.
_APP_NAME = "MarkItDown"
_APP_AUTHOR = "Microsoft"

# Subdirectory names within the user data dir.
_CONFIG_DIR = "config"
_LOGS_DIR = "logs"


def user_data_path() -> Path:
    """Root user data directory. Created if missing.

    Windows: %APPDATA%\\Microsoft\\MarkItDown
    macOS:   ~/Library/Application Support/Microsoft/MarkItDown
    Linux:   ~/.local/share/Microsoft/MarkItDown  (not officially supported)
    """
    path = Path(user_data_dir(_APP_NAME, _APP_AUTHOR, roaming=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    """Directory holding config.json and friends."""
    p = user_data_path() / _CONFIG_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_file() -> Path:
    """Path to the JSON config file."""
    return config_dir() / "config.json"


def logs_dir() -> Path:
    """Directory for log files (used in Phase 6+ for crash logs)."""
    p = Path(user_log_dir(_APP_NAME, _APP_AUTHOR))
    if not p.exists():
        # user_log_dir() may point somewhere the app can't write; fall back.
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            fallback = user_data_path() / _LOGS_DIR
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
    return p


def fallback_secrets_file() -> Path:
    """Path to the encrypted-JSON fallback used when keyring is unavailable.

    File is created lazily; only its path is announced here.
    """
    return config_dir() / "secrets.enc.json"

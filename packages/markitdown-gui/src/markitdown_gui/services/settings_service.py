"""Settings persistence: keyring for secrets, JSON for the rest.

Two storage backends behind one facade:

- **Secrets** (API keys): OS keyring when available, encrypted-JSON fallback
  (Fernet + user-provided password) when not.
- **Config** (everything else): plain JSON at
  `paths_service.config_file()`.

The service is intentionally small and synchronous — it's called from the
Flet UI thread for reads (cheap) and from a background worker for writes
(via the converter service in Phase 3).
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import keyring
import keyring.errors
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from markitdown import MarkItDown  # type: ignore[import-untyped]

from ..models.config import AppConfig
from . import paths_service


# --- Secret naming ---------------------------------------------------------

KEYRING_SERVICE = "markitdown-gui"
"""Service name registered in the OS keyring."""

# Tuple of all secret field names — kept in sync with what the UI writes.
SECRET_FIELDS: tuple[str, ...] = (
    "openai_api_key",
    "docintel_key",
    "cu_key",
)


# --- Settings service ------------------------------------------------------


class SettingsService:
    """Single entry point for all persistence and MarkItDown construction.

    Keyring failures (sandboxed macOS, headless Linux, broken credential
    store on Windows) are caught and the service transparently falls back
    to an encrypted local file. `keyring_available` in AppConfig reflects
    the current state so the UI can show a warning.
    """

    def __init__(self) -> None:
        self._config_path = paths_service.config_file()
        self._fallback_path = paths_service.fallback_secrets_file()
        self._config: AppConfig = self._load_config()
        # Probe keyring on init; remember the verdict for the lifetime of
        # the process. If it ever starts working, the user can restart.
        self._keyring_ok: bool = self._probe_keyring()
        self._config.keyring_available = self._keyring_ok

    # --- Public: config ---------------------------------------------------

    def get_config(self) -> AppConfig:
        return self._config

    def save_config(self, new_config: AppConfig) -> None:
        """Persist the config atomically (write to .tmp, then rename)."""
        new_config.keyring_available = self._keyring_ok
        self._config = new_config
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._config_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(new_config.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, self._config_path)

    # --- Public: secrets ---------------------------------------------------

    def get_secret(self, name: str) -> str | None:
        if name not in SECRET_FIELDS:
            raise ValueError(f"Unknown secret field: {name!r}")
        if self._keyring_ok:
            try:
                value = keyring.get_password(KEYRING_SERVICE, name)
                return value if value else None
            except keyring.errors.KeyringError:
                # keyring stopped working mid-session; fall through to fallback
                self._keyring_ok = False
                self._config.keyring_available = False
        return self._fallback_get(name)

    def set_secret(self, name: str, value: str) -> None:
        if name not in SECRET_FIELDS:
            raise ValueError(f"Unknown secret field: {name!r}")
        if self._keyring_ok:
            try:
                keyring.set_password(KEYRING_SERVICE, name, value)
                # Mirror to fallback so a future keyring outage still has data
                self._fallback_set(name, value)
                return
            except keyring.errors.KeyringError:
                self._keyring_ok = False
                self._config.keyring_available = False
        self._fallback_set(name, value)

    def delete_secret(self, name: str) -> None:
        if name not in SECRET_FIELDS:
            raise ValueError(f"Unknown secret field: {name!r}")
        if self._keyring_ok:
            try:
                keyring.delete_password(KEYRING_SERVICE, name)
            except keyring.errors.PasswordDeleteError:
                pass  # already absent
            except keyring.errors.KeyringError:
                self._keyring_ok = False
        self._fallback_delete(name)

    # --- Public: factory --------------------------------------------------

    def build_markitdown(self) -> MarkItDown:
        """Construct a fresh MarkItDown with the current config + secrets.

        Called once per conversion (in Phase 3) so that settings changes
        take effect immediately. Returns a MarkItDown with all built-in
        converters enabled; if the user has set an `enabled_plugins`
        allowlist, non-listed plugin converters are removed from
        `md._converters` after construction.
        """
        cfg = self._config

        kwargs: dict[str, Any] = {
            "enable_builtins": True,
            "enable_plugins": True,  # always load; we filter below
            "exiftool_path": cfg.exiftool_path,
            "style_map": cfg.style_map,
            "keep_data_uris": cfg.keep_data_uris,
        }

        # --- LLM (OpenAI-compatible) ---
        if cfg.openai_base_url and cfg.openai_model and (api_key := self.get_secret("openai_api_key")):
            try:
                from openai import OpenAI

                kwargs["llm_client"] = OpenAI(base_url=cfg.openai_base_url, api_key=api_key)
                kwargs["llm_model"] = cfg.openai_model
            except Exception:
                # Don't break the conversion because LLM setup failed;
                # image description will be skipped silently.
                pass

        # --- Document Intelligence ---
        if cfg.docintel_endpoint and (key := self.get_secret("docintel_key")):
            try:
                from azure.core.credentials import AzureKeyCredential

                kwargs["docintel_endpoint"] = cfg.docintel_endpoint
                kwargs["docintel_credential"] = AzureKeyCredential(key)
                if cfg.docintel_api_version:
                    kwargs["docintel_api_version"] = cfg.docintel_api_version
            except Exception:
                pass

        # --- Content Understanding ---
        if cfg.cu_endpoint and (key := self.get_secret("cu_key")):
            try:
                from azure.core.credentials import AzureKeyCredential

                kwargs["cu_endpoint"] = cfg.cu_endpoint
                kwargs["cu_credential"] = AzureKeyCredential(key)
                if cfg.cu_analyzer_id:
                    kwargs["cu_analyzer_id"] = cfg.cu_analyzer_id
                if cfg.cu_file_types:
                    kwargs["cu_file_types"] = cfg.cu_file_types
            except Exception:
                pass

        md = MarkItDown(**kwargs)

        # --- Plugin allowlist filtering ---
        # MarkItDown has no per-plugin flag; remove non-listed ones after load.
        if cfg.enabled_plugins:
            keep = set(cfg.enabled_plugins)
            md._converters = [
                reg
                for reg in md._converters
                if reg.converter.__class__.__module__.split(".")[0] in keep
            ]

        return md

    # --- Internals: config I/O -------------------------------------------

    def _load_config(self) -> AppConfig:
        if not self._config_path.exists():
            return AppConfig()
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return AppConfig()
        if not isinstance(data, dict):
            return AppConfig()
        return AppConfig.from_dict(data)

    # --- Internals: keyring probe ----------------------------------------

    def _probe_keyring(self) -> bool:
        """Try a no-op write+read+delete against the keyring.

        If anything fails, return False and the service will use fallback
        storage for the rest of the session.
        """
        probe_key = "__markitdown_probe__"
        try:
            keyring.set_password(KEYRING_SERVICE, probe_key, "ok")
            got = keyring.get_password(KEYRING_SERVICE, probe_key)
            try:
                keyring.delete_password(KEYRING_SERVICE, probe_key)
            except keyring.errors.PasswordDeleteError:
                pass
            return got == "ok"
        except keyring.errors.KeyringError:
            return False
        except Exception:
            return False

    # --- Internals: encrypted-JSON fallback ------------------------------

    def _fallback_load_all(self) -> dict[str, str]:
        if not self._fallback_path.exists():
            return {}
        password = self._get_fallback_password()
        if password is None:
            return {}
        try:
            token = self._fallback_path.read_bytes()
            payload = json.loads(Fernet(self._derive_key(password)).decrypt(token).decode("utf-8"))
            return {k: v for k, v in payload.items() if k in SECRET_FIELDS}
        except (InvalidToken, json.JSONDecodeError, OSError, ValueError):
            return {}

    def _fallback_save_all(self, data: dict[str, str]) -> None:
        password = self._set_fallback_password()
        token = Fernet(self._derive_key(password)).encrypt(
            json.dumps(data, ensure_ascii=False).encode("utf-8")
        )
        self._fallback_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._fallback_path.with_suffix(".enc.json.tmp")
        tmp.write_bytes(token)
        os.replace(tmp, self._fallback_path)

    def _fallback_get(self, name: str) -> str | None:
        return self._fallback_load_all().get(name)

    def _fallback_set(self, name: str, value: str) -> None:
        data = self._fallback_load_all()
        data[name] = value
        self._fallback_save_all(data)

    def _fallback_delete(self, name: str) -> None:
        data = self._fallback_load_all()
        data.pop(name, None)
        self._fallback_save_all(data)

    # --- Internals: fallback password (in env) ---------------------------

    _FALLBACK_PASSWORD_ENV = "MARKITDOWN_GUI_FALLBACK_PWD"

    def _get_fallback_password(self) -> str | None:
        return os.environ.get(self._FALLBACK_PASSWORD_ENV)

    def _set_fallback_password(self) -> str:
        """Reuse existing env password, or generate + persist one in env.

        v1 uses a process-env password (random per launch). The first
        fallback write in a session generates the password; subsequent
        writes reuse it. On next launch a new password is generated,
        meaning secrets written in a previous session cannot be read
        back. This is acceptable for v1 since secrets are usually
        entered fresh; a proper user-password flow ships in v1.1.
        """
        existing = self._get_fallback_password()
        if existing:
            return existing
        # 32 random bytes -> 64 hex chars. Not a true user password, but
        # enough to keep plaintext off disk while we wire up the prompt UI.
        import secrets as _secrets

        pwd = _secrets.token_hex(32)
        os.environ[self._FALLBACK_PASSWORD_ENV] = pwd
        return pwd

    @staticmethod
    def _derive_key(password: str) -> bytes:
        """Derive a Fernet key from a password.

        Uses a fixed salt for v1 (acceptable because the password is
        already random 32 bytes). A per-install salt + user-chosen
        password flow lands in v1.1.
        """
        salt = b"markitdown-gui-fallback-salt-v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=120_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

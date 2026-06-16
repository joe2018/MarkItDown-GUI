"""Settings view: cloud config, output preferences, advanced.

All fields are bound to a local draft AppConfig; the user clicks "Save"
to persist (which also pushes secrets to keyring). "Test connection"
buttons run lightweight probes against the entered credentials.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

import flet as ft

from ..components.key_input import key_input
from ..i18n import T
from ..models.config import AppConfig
from ..services.settings_service import SettingsService


logger = logging.getLogger(__name__)


# --- Test-connection probes -----------------------------------------------


def _probe_llm(base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        return False, f"openai 包缺失: {exc}"
    if not (base_url and api_key and model):
        return False, "缺少 Base URL / API Key / Model"
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        return True, ""
    except Exception as exc:
        return False, _short_error(exc)


def _probe_cu(endpoint: str, key: str) -> tuple[bool, str]:
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.ai.contentunderstanding import ContentUnderstandingClient
    except ImportError as exc:
        return False, f"azure-ai-contentunderstanding 包缺失: {exc}"
    if not (endpoint and key):
        return False, "缺少 Endpoint / API Key"
    try:
        client = ContentUnderstandingClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )
        # get_analyzer is a lightweight probe (no document quota).
        client.get_analyzer("prebuilt-documentSearch")
        return True, ""
    except Exception as exc:
        return False, _short_error(exc)


def _probe_docintel(endpoint: str, key: str) -> tuple[bool, str]:
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.ai.documentintelligence import DocumentIntelligenceClient
    except ImportError as exc:
        return False, f"azure-ai-documentintelligence 包缺失: {exc}"
    if not (endpoint and key):
        return False, "缺少 Endpoint / API Key"
    try:
        # Construction validates endpoint + credential; no API call is made.
        DocumentIntelligenceClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )
        return True, ""
    except Exception as exc:
        return False, _short_error(exc)


def _short_error(exc: BaseException) -> str:
    msg = str(exc).strip()
    # Trim long Azure SDK error messages
    return msg[:160] + ("…" if len(msg) > 160 else "")


# --- The view --------------------------------------------------------------


class SettingsView:
    """Class so we can hold mutable field state across rebuilds."""

    def __init__(self, page: ft.Page, settings: SettingsService, on_back: Callable[[], None]) -> None:
        self.page = page
        self.settings = settings
        self.on_back = on_back
        # Draft config (copy of current; only persisted on Save)
        self._draft: AppConfig = AppConfig.from_dict(settings.get_config().to_dict())
        # Current values for the three secret fields, held in-memory
        # until Save is pressed.
        self._secrets: dict[str, str | None] = {
            "openai_api_key": settings.get_secret("openai_api_key"),
            "docintel_key": settings.get_secret("docintel_key"),
            "cu_key": settings.get_secret("cu_key"),
        }
        # Field refs for testing
        self._test_result_text: dict[str, ft.Text] = {}
        self._root: ft.Container | None = None

    def build(self) -> ft.Control:
        self._root = ft.Container(content=self._build_content(), expand=True)
        return self._root

    # --- Content ---------------------------------------------------------

    def _build_content(self) -> ft.Control:
        cfg = self._draft
        scroll = ft.Column(
            [
                self._build_top_bar(),
                ft.Container(padding=8),
                self._build_llm_section(),
                ft.Container(height=12),
                self._build_docintel_section(),
                ft.Container(height=12),
                self._build_cu_section(),
                ft.Container(height=12),
                self._build_output_section(),
                ft.Container(height=12),
                self._build_advanced_section(),
                ft.Container(height=24),
                self._build_bottom_bar(),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
        )
        return ft.Container(content=scroll, padding=ft.padding.symmetric(horizontal=24, vertical=8), expand=True)

    def _build_top_bar(self) -> ft.Control:
        return ft.Row(
            [
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: self.on_back()),
                ft.Text(T.nav_settings, size=22, weight=ft.FontWeight.BOLD),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # --- Sections --------------------------------------------------------

    def _section(self, title: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [ft.Text(title, size=15, weight=ft.FontWeight.W_600), ft.Container(padding=6), *controls],
                spacing=8,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
        )

    def _test_result_label(self, key: str) -> ft.Text:
        if key not in self._test_result_text:
            self._test_result_text[key] = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        return self._test_result_text[key]

    def _build_llm_section(self) -> ft.Control:
        cfg = self._draft
        base_url = ft.TextField(
            label=T.field_base_url,
            value=cfg.openai_base_url or "",
            on_change=lambda e: setattr(self._draft, "openai_base_url", e.control.value or None),
            expand=True,
        )
        model = ft.TextField(
            label=T.field_model,
            value=cfg.openai_model or "",
            on_change=lambda e: setattr(self._draft, "openai_model", e.control.value or None),
            expand=True,
        )
        api_key = key_input(
            label=T.field_api_key,
            initial_value=self._secrets.get("openai_api_key"),
            on_change=lambda v: self._secrets.__setitem__("openai_api_key", v),
        )
        test_row = ft.Row(
            [
                ft.OutlinedButton(
                    T.test_connection,
                    icon=ft.Icons.NETWORK_CHECK,
                    on_click=lambda _: self._run_test("llm", _probe_llm, base_url.value, self._secrets.get("openai_api_key") or "", model.value),
                ),
                self._test_result_label("llm"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return self._section(T.settings_section_llm, [base_url, model, api_key, test_row])

    def _build_docintel_section(self) -> ft.Control:
        cfg = self._draft
        endpoint = ft.TextField(
            label=T.field_endpoint,
            value=cfg.docintel_endpoint or "",
            on_change=lambda e: setattr(self._draft, "docintel_endpoint", e.control.value or None),
            expand=True,
        )
        api_version = ft.TextField(
            label=T.field_api_version,
            value=cfg.docintel_api_version or "",
            on_change=lambda e: setattr(self._draft, "docintel_api_version", e.control.value or None),
            expand=True,
        )
        api_key = key_input(
            label=T.field_api_key,
            initial_value=self._secrets.get("docintel_key"),
            on_change=lambda v: self._secrets.__setitem__("docintel_key", v),
        )
        test_row = ft.Row(
            [
                ft.OutlinedButton(
                    T.test_connection,
                    icon=ft.Icons.NETWORK_CHECK,
                    on_click=lambda _: self._run_test("docintel", _probe_docintel, endpoint.value, self._secrets.get("docintel_key") or ""),
                ),
                self._test_result_label("docintel"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return self._section(T.settings_section_docintel, [endpoint, api_version, api_key, test_row])

    def _build_cu_section(self) -> ft.Control:
        cfg = self._draft
        endpoint = ft.TextField(
            label=T.field_endpoint,
            value=cfg.cu_endpoint or "",
            on_change=lambda e: setattr(self._draft, "cu_endpoint", e.control.value or None),
            expand=True,
        )
        analyzer = ft.TextField(
            label=T.field_analyzer,
            value=cfg.cu_analyzer_id or "",
            on_change=lambda e: setattr(self._draft, "cu_analyzer_id", e.control.value or None),
            expand=True,
        )
        file_types = ft.TextField(
            label=T.field_cu_file_types,
            value=", ".join(cfg.cu_file_types),
            on_change=lambda e: setattr(
                self._draft, "cu_file_types", [s.strip() for s in (e.control.value or "").split(",") if s.strip()]
            ),
            expand=True,
        )
        api_key = key_input(
            label=T.field_api_key,
            initial_value=self._secrets.get("cu_key"),
            on_change=lambda v: self._secrets.__setitem__("cu_key", v),
        )
        test_row = ft.Row(
            [
                ft.OutlinedButton(
                    T.test_connection,
                    icon=ft.Icons.NETWORK_CHECK,
                    on_click=lambda _: self._run_test("cu", _probe_cu, endpoint.value, self._secrets.get("cu_key") or ""),
                ),
                self._test_result_label("cu"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return self._section(T.settings_section_cu, [endpoint, analyzer, file_types, api_key, test_row])

    def _build_output_section(self) -> ft.Control:
        cfg = self._draft
        output_dir = ft.TextField(
            label=T.field_output_dir,
            value=cfg.default_output_dir or "",
            hint_text=T.field_output_dir_same,
            on_change=lambda e: setattr(self._draft, "default_output_dir", e.control.value or None),
            expand=True,
        )
        keep_uris = ft.Checkbox(
            label=T.field_keep_data_uris,
            value=cfg.keep_data_uris,
            on_change=lambda e: setattr(self._draft, "keep_data_uris", e.control.value),
        )
        return self._section(T.settings_section_output, [output_dir, keep_uris])

    def _build_advanced_section(self) -> ft.Control:
        cfg = self._draft
        exiftool = ft.TextField(
            label=T.field_exiftool,
            value=cfg.exiftool_path or "",
            hint_text=T.field_exiftool_auto,
            on_change=lambda e: setattr(self._draft, "exiftool_path", e.control.value or None),
            expand=True,
        )
        warning = ft.Container()
        if not cfg.keyring_available:
            warning = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.AMBER),
                        ft.Container(width=8),
                        ft.Text(T.warning_keyring_fallback, size=12, color=ft.Colors.AMBER, expand=True),
                    ]
                ),
                padding=8,
                border=ft.border.all(1, ft.Colors.AMBER),
                border_radius=6,
                bgcolor=ft.Colors.AMBER_50,
            )
        return self._section(T.settings_section_advanced, [exiftool, warning])

    def _build_bottom_bar(self) -> ft.Control:
        return ft.Row(
            [
                ft.Container(expand=True),
                ft.OutlinedButton(T.settings_cancel, on_click=lambda _: self.on_back()),
                ft.FilledButton(T.settings_save, icon=ft.Icons.SAVE, on_click=lambda _: self._on_save()),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # --- Test connection -------------------------------------------------

    def _run_test(self, key: str, probe, *args) -> None:
        label = self._test_result_label(key)
        label.value = T.test_running
        label.color = ft.Colors.ON_SURFACE_VARIANT
        label.update()

        def _do():
            ok, err = probe(*args)
            if ok:
                label.value = T.test_success
                label.color = ft.Colors.GREEN
            else:
                label.value = T.test_failure(err)
                label.color = ft.Colors.RED
            try:
                label.update()
            except Exception:
                pass

        threading.Thread(target=_do, daemon=True).start()

    # --- Save ------------------------------------------------------------

    def _on_save(self) -> None:
        self.settings.save_config(self._draft)
        for name, value in self._secrets.items():
            if value:
                self.settings.set_secret(name, value)
            else:
                self.settings.delete_secret(name)
        self._show_snackbar(T.settings_saved)
        self.on_back()

    def _show_snackbar(self, msg: str) -> None:
        self.page.snack_bar = ft.SnackBar(content=ft.Text(msg), open=True)
        self.page.update()

"""Plugins view: list installed plugins, toggle each on/off."""

from __future__ import annotations

import logging
from typing import Callable

import flet as ft

from ..i18n import T
from ..models.plugin_info import PluginInfo
from ..services import plugin_service
from ..services.settings_service import SettingsService


logger = logging.getLogger(__name__)


class PluginsView:
    def __init__(
        self,
        page: ft.Page,
        settings: SettingsService,
        on_back: Callable[[], None],
    ) -> None:
        self.page = page
        self.settings = settings
        self.on_back = on_back
        self._plugins: list[PluginInfo] = []
        self._root: ft.Container | None = None

    def build(self) -> ft.Control:
        self._refresh_list()
        self._root = ft.Container(content=self._build_content(), expand=True)
        return self._root

    def _refresh_list(self) -> None:
        self._plugins = plugin_service.list_installed_plugins(self.settings.get_config())

    def _build_content(self) -> ft.Control:
        top_bar = ft.Row(
            [
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: self.on_back()),
                ft.Text(T.nav_plugins, size=22, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.IconButton(
                    ft.Icons.REFRESH,
                    tooltip=T.plugins_refresh,
                    on_click=lambda _: self._on_refresh(),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if not self._plugins:
            list_view = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(T.plugins_empty, color=ft.Colors.ON_SURFACE_VARIANT, size=13),
                        ft.Container(height=12),
                        ft.Text(T.plugins_install_hint, color=ft.Colors.ON_SURFACE_VARIANT, size=12),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                ),
                padding=24,
                alignment=ft.alignment.top_center,
            )
        else:
            list_view = ft.Column(
                [self._build_plugin_card(p) for p in self._plugins],
                spacing=8,
            )

        warning = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Container(width=8),
                    ft.Text(T.plugin_load_warning, size=11, color=ft.Colors.ON_SURFACE_VARIANT, expand=True),
                ]
            ),
            padding=8,
        )

        scroll = ft.Column(
            [top_bar, ft.Container(padding=8), list_view, warning],
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
        )
        return ft.Container(content=scroll, padding=ft.padding.symmetric(horizontal=24, vertical=8), expand=True)

    def _build_plugin_card(self, p: PluginInfo) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.EXTENSION if p.enabled else ft.Icons.EXTENSION_OFF,
                        color=ft.Colors.PRIMARY if p.enabled else ft.Colors.ON_SURFACE_VARIANT,
                        size=24,
                    ),
                    ft.Container(width=12),
                    ft.Column(
                        [
                            ft.Text(p.module, size=14, weight=ft.FontWeight.W_600),
                            ft.Text(
                                f"{T.plugins_version}: {p.version}    {T.plugins_source}: {p.distribution}",
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Switch(
                        label=T.plugins_enable,
                        value=p.enabled,
                        on_change=lambda e: self._on_toggle(p, e.control.value),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
        )

    # --- Handlers --------------------------------------------------------

    def _on_refresh(self) -> None:
        if self._root is not None:
            self._refresh_list()
            self._root.content = self._build_content()
            self.page.update()

    def _on_toggle(self, plugin: PluginInfo, enabled: bool) -> None:
        new_cfg = plugin_service.set_plugin_enabled(plugin, enabled, self.settings.get_config())
        self.settings.save_config(new_cfg)
        # Update local state + UI
        for p in self._plugins:
            if p.module == plugin.module:
                p.enabled = enabled
                break
        if self._root is not None:
            self._root.content = self._build_content()
            self.page.update()

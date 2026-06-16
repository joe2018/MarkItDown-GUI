"""Flet app root: navigation shell, theme, page bootstrap.

Phase 1: minimal shell with 4 placeholder pages.
Phase 3: Home view is wired to HomeView; Settings/Plugins/About remain
placeholders that subsequent phases will fill in.
"""

import flet as ft

from . import __version__
from .i18n import T
from .services.settings_service import SettingsService
from .theme import AppTheme
from .views.about_view import about_view
from .views.home_view import HomeView
from .views.plugins_view import PluginsView
from .views.settings_view import SettingsView


def main(page: ft.Page) -> None:
    """The Flet entry point. Called once when the app starts."""
    # --- Page-level config ---
    page.title = T.app_title
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 900
    page.window.min_height = 600
    # Flet 0.28 derives brightness from page.theme_mode. Both themes
    # share the same seed; Flet auto-derives the dark variant.
    page.theme = ft.Theme(color_scheme_seed=AppTheme.PRIMARY_SEED)
    page.dark_theme = ft.Theme(color_scheme_seed=AppTheme.PRIMARY_SEED)

    # --- Services (singletons for the session) ---
    settings = SettingsService()
    home_view = HomeView(page, settings)

    # --- Cleanup on close ---
    def _on_window_event(e: ft.WindowEvent) -> None:
        if e.type == ft.WindowEventType.CLOSE:
            home_view.shutdown()

    page.on_window_event = _on_window_event

    # --- Pages ---
    settings_view = SettingsView(page, settings, on_back=lambda: _on_nav_change(0))
    plugins_view = PluginsView(page, settings, on_back=lambda: _on_nav_change(0))
    about_view_control = about_view(on_back=lambda: _on_nav_change(0))

    page_views: list[ft.Control] = [
        home_view.build(),
        settings_view.build(),
        plugins_view.build(),
        about_view_control,
    ]

    # --- Navigation rail ---
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        min_extended_width=200,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME,
                label=T.nav_home,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label=T.nav_settings,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.EXTENSION_OUTLINED,
                selected_icon=ft.Icons.EXTENSION,
                label=T.nav_plugins,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.INFO_OUTLINED,
                selected_icon=ft.Icons.INFO,
                label=T.nav_about,
            ),
        ],
        on_change=lambda e: _on_nav_change(e.control.selected_index or 0),
    )

    body = ft.Container(content=page_views[0], expand=True)

    def _on_nav_change(new_index: int) -> None:
        body.content = page_views[new_index]
        page.update()

    # --- Top bar with version badge ---
    top_bar = ft.Container(
        content=ft.Row(
            [
                ft.Text(T.app_title, size=20, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Chip(
                    label=ft.Text(f"v{__version__}"),
                    bgcolor=ft.Colors.SECONDARY_CONTAINER,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        bgcolor=ft.Colors.SURFACE,
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
    )

    # --- Layout ---
    page.add(
        ft.Column(
            [
                top_bar,
                ft.Row(
                    [rail, ft.VerticalDivider(width=1), body],
                    expand=True,
                    spacing=0,
                ),
            ],
            expand=True,
            spacing=0,
        )
    )
    page.update()

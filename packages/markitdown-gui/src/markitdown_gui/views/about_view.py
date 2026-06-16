"""About view: version info and external links."""

from __future__ import annotations

import platform
import sys
from typing import Callable

import flet as ft

from .. import __version__
from ..i18n import T


def about_view(on_back: Callable[[], None]) -> ft.Control:
    """Build the about page (functional, no state)."""
    try:
        from importlib.metadata import version as _pkg_version

        flet_version = _pkg_version("flet")
    except Exception:
        flet_version = "unknown"

    try:
        from markitdown import __version__ as markitdown_version
    except Exception:
        markitdown_version = "unknown"

    def _link_row(icon: str, text: str) -> ft.Control:
        return ft.Row(
            [ft.Icon(icon, size=18, color=ft.Colors.PRIMARY), ft.Container(width=8), ft.Text(text, size=13)],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    body = ft.Column(
        [
            ft.Row(
                [
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: on_back()),
                    ft.Text(T.nav_about, size=22, weight=ft.FontWeight.BOLD),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(padding=8),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"MarkItDown GUI  v{__version__}", size=24, weight=ft.FontWeight.BOLD),
                        ft.Container(height=4),
                        ft.Text(T.about_subtitle, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Container(height=24),
                        ft.Row(
                            [
                                ft.Text(f"{T.about_core_version}:", size=13, weight=ft.FontWeight.W_500, width=140),
                                ft.Text(str(markitdown_version), size=13),
                            ]
                        ),
                        ft.Container(height=6),
                        ft.Row(
                            [
                                ft.Text(f"{T.about_flet_version}:", size=13, weight=ft.FontWeight.W_500, width=140),
                                ft.Text(str(flet_version), size=13),
                            ]
                        ),
                        ft.Container(height=6),
                        ft.Row(
                            [
                                ft.Text(f"{T.about_python_version}:", size=13, weight=ft.FontWeight.W_500, width=140),
                                ft.Text(platform.python_version(), size=13),
                            ]
                        ),
                        ft.Container(height=24),
                        _link_row(ft.Icons.CODE, T.about_github),
                        ft.Container(height=6),
                        _link_row(ft.Icons.DESCRIPTION, T.about_docs),
                        ft.Container(height=24),
                        ft.Text(T.about_license, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                ),
                padding=32,
                alignment=ft.alignment.top_center,
                expand=True,
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
    )
    return ft.Container(content=body, padding=ft.padding.symmetric(horizontal=24, vertical=8), expand=True)

"""Drop zone: the large clickable + droppable area at the top of Home.

The visual is just a styled Container; the actual drag-and-drop is
handled by `page.on_file_drop` set in app.py. The click action invokes
a FilePicker that's also created in app.py and passed in here.
"""

from __future__ import annotations

import flet as ft

from ..i18n import T


def drop_zone(on_click: Callable[[], None]) -> ft.Control:
    """Return a large, friendly drop target. Click triggers on_click."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.CLOUD_UPLOAD_OUTLINED,
                    size=64,
                    color=ft.Colors.PRIMARY,
                ),
                ft.Container(height=8),
                ft.Text(
                    T.home_drop_title,
                    size=18,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(height=4),
                ft.Text(
                    T.home_drop_subtitle,
                    size=13,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Container(height=12),
                ft.OutlinedButton(
                    T.home_drop_browse,
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda _: on_click(),
                ),
                ft.Container(height=12),
                ft.Text(
                    T.home_drop_supported,
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=0,
        ),
        height=200,
        border=ft.border.all(2, ft.Colors.OUTLINE_VARIANT),
        border_radius=12,
        bgcolor=ft.Colors.SURFACE,
        alignment=ft.alignment.center,
        ink=True,
        on_click=lambda _: on_click(),
    )

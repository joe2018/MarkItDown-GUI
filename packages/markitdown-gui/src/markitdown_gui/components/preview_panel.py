"""Preview panel: shows the markdown result of a completed job.

Read-only monospace view. Action buttons copy to clipboard or save to a
different location.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from ..i18n import T
from ..models.job import ConversionJob


def preview_panel(
    job: ConversionJob | None,
    on_copy: Callable[[str], None],
    on_save_as: Callable[[str, str], None],
) -> ft.Control:
    """Return a panel showing the job's markdown (or empty-state)."""
    if job is None or job.markdown is None:
        return ft.Container(
            content=ft.Text(
                T.home_preview_empty,
                color=ft.Colors.ON_SURFACE_VARIANT,
                size=13,
            ),
            padding=24,
            alignment=ft.alignment.center,
            expand=True,
        )

    markdown_text = job.markdown
    filename = job.source_path.name

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ARTICLE, size=18, color=ft.Colors.PRIMARY),
                        ft.Container(width=8),
                        ft.Text(
                            filename,
                            size=14,
                            weight=ft.FontWeight.W_600,
                            expand=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.TextButton(
                            T.home_action_copy,
                            icon=ft.Icons.COPY,
                            on_click=lambda _: on_copy(markdown_text),
                        ),
                        ft.TextButton(
                            T.home_action_save_as,
                            icon=ft.Icons.SAVE_ALT,
                            on_click=lambda _: on_save_as(markdown_text, filename),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Text(
                        markdown_text,
                        font_family="monospace",
                        size=12,
                        selectable=True,
                    ),
                    bgcolor=ft.Colors.SURFACE,
                    border_radius=8,
                    padding=12,
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        ),
        padding=16,
        expand=True,
    )

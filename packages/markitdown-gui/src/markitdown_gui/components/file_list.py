"""File list: vertical stack of JobCards, with empty-state placeholder."""

from __future__ import annotations

from typing import Callable, Iterable

import flet as ft

from ..i18n import T
from ..models.job import ConversionJob
from .job_card import (
    OnCancel,
    OnCopyPip,
    OnDelete,
    OnOpenFolder,
    OnPreview,
    OnRetry,
    job_card,
)


def file_list(
    jobs: Iterable[ConversionJob],
    on_preview: OnPreview,
    on_open_folder: OnOpenFolder,
    on_cancel: OnCancel,
    on_retry: OnRetry,
    on_delete: OnDelete,
    on_copy_pip: OnCopyPip,
) -> ft.Control:
    """Build a scrollable column of job cards, or an empty-state."""
    job_list = list(jobs)
    if not job_list:
        return ft.Container(
            content=ft.Text(
                T.home_tasks_empty,
                color=ft.Colors.ON_SURFACE_VARIANT,
                size=13,
            ),
            padding=24,
            alignment=ft.alignment.center,
        )

    return ft.Column(
        [
            job_card(j, on_preview, on_open_folder, on_cancel, on_retry, on_delete, on_copy_pip)
            for j in job_list
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

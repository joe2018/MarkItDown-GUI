"""Job card: one row per file, showing status / progress / actions.

Pure UI; the parent (HomeView) passes in callbacks for each action so
the card never reaches into the converter service directly.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from ..i18n import T
from ..models.job import ConversionJob, JobStatus
from .status_icon import status_icon


# Public callback signatures
OnPreview = Callable[[ConversionJob], None]
OnOpenFolder = Callable[[ConversionJob], None]
OnCancel = Callable[[ConversionJob], None]
OnRetry = Callable[[ConversionJob], None]
OnDelete = Callable[[ConversionJob], None]
OnCopyPip = Callable[[ConversionJob], None]


def job_card(
    job: ConversionJob,
    on_preview: OnPreview,
    on_open_folder: OnOpenFolder,
    on_cancel: OnCancel,
    on_retry: OnRetry,
    on_delete: OnDelete,
    on_copy_pip: OnCopyPip,
) -> ft.Control:
    """Build a single job row. Pure function of `job` + callbacks."""
    status_label = _status_label(job)

    # --- Progress: indeterminate for running, hidden for terminal states
    if job.status == JobStatus.RUNNING:
        progress = ft.ProgressRing(width=16, height=16, stroke_width=2)
    else:
        progress = ft.Container(width=16)  # spacer

    # --- Action buttons (vary by status) ---
    actions: list[ft.Control] = []
    if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
        actions.append(
            ft.TextButton(T.home_action_cancel, on_click=lambda _: on_cancel(job))
        )
    if job.status == JobStatus.DONE:
        actions.append(
            ft.TextButton(T.home_action_preview, on_click=lambda _: on_preview(job))
        )
        actions.append(
            ft.TextButton(T.home_action_open_folder, on_click=lambda _: on_open_folder(job))
        )
    if job.status == JobStatus.FAILED:
        actions.append(
            ft.TextButton(T.home_action_retry, on_click=lambda _: on_retry(job))
        )
        if job.error_install_hint:
            actions.append(
                ft.TextButton(
                    T.home_action_copy_pip,
                    on_click=lambda _: on_copy_pip(job),
                )
            )
    if job.status == JobStatus.CANCELLED:
        actions.append(
            ft.TextButton(T.home_action_retry, on_click=lambda _: on_retry(job))
        )

    # Delete button: available in every state EXCEPT running (a running
    # job holds a thread + may be writing output; remove only via cancel).
    if job.status != JobStatus.RUNNING:
        actions.append(
            ft.IconButton(
                ft.Icons.DELETE_OUTLINE,
                tooltip=T.home_action_delete,
                on_click=lambda _: on_delete(job),
            )
        )

    # --- Error / hint text (only when failed) ---
    info_text: list[ft.Control] = []
    if job.status == JobStatus.FAILED:
        info_text.append(
            ft.Text(
                job.error or T.error_unknown,
                size=12,
                color=ft.Colors.RED,
                weight=ft.FontWeight.W_500,
            )
        )
        if job.error_install_hint:
            info_text.append(
                ft.Text(
                    job.error_install_hint,
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    font_family="monospace",
                )
            )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        status_icon(job.status),
                        ft.Container(width=8),
                        ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Container(width=6),
                        ft.Text(
                            job.source_path.name,
                            size=14,
                            weight=ft.FontWeight.W_500,
                            expand=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(status_label, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        progress,
                        ft.Container(width=8),
                        *actions,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                *info_text,
            ],
            spacing=2,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
    )


def _status_label(job: ConversionJob) -> str:
    return {
        JobStatus.PENDING: T.home_status_pending,
        JobStatus.RUNNING: T.home_status_running,
        JobStatus.DONE: T.home_status_done,
        JobStatus.FAILED: T.home_status_failed,
        JobStatus.CANCELLED: T.home_status_cancelled,
    }[job.status]

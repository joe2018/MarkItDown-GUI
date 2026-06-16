"""Status icon: maps a JobStatus to a colored Flet Icon."""

from __future__ import annotations

import flet as ft

from ..models.job import JobStatus


_COLOR_MAP: dict[JobStatus, ft.Colors] = {
    JobStatus.PENDING: ft.Colors.OUTLINE,
    JobStatus.RUNNING: ft.Colors.BLUE,
    JobStatus.DONE: ft.Colors.GREEN,
    JobStatus.FAILED: ft.Colors.RED,
    JobStatus.CANCELLED: ft.Colors.ORANGE,
}

_ICON_MAP: dict[JobStatus, str] = {
    JobStatus.PENDING: ft.Icons.SCHEDULE,
    JobStatus.RUNNING: ft.Icons.AUTORENEW,
    JobStatus.DONE: ft.Icons.CHECK_CIRCLE,
    JobStatus.FAILED: ft.Icons.ERROR,
    JobStatus.CANCELLED: ft.Icons.CANCEL,
}


def status_icon(status: JobStatus) -> ft.Control:
    """Return a small colored icon for the given job status."""
    return ft.Icon(
        _ICON_MAP[status],
        color=_COLOR_MAP[status],
        size=20,
    )

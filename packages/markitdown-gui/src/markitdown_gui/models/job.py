"""Conversion job model: tracks one file's progress through the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ConversionJob:
    """One file's conversion lifecycle.

    `output_path` is computed at creation time from `source_path` so the UI
    can show "save to ..." before the conversion runs. The converter may
    override it on success.
    """

    source_path: Path
    output_path: Path
    id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0  # 0.0 - 1.0; -1.0 means indeterminate
    error: str | None = None
    error_install_hint: str | None = None  # e.g. "pip install markitdown[pdf]"
    markdown: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

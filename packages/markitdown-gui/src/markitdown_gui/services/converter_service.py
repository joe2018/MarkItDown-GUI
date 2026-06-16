"""Background conversion service.

Wraps the markitdown core with:

- A thread pool (max 2 workers, to avoid hammering cloud APIs)
- Cancellation via per-job threading.Event
- Progress + completion callbacks that the Flet UI can hook into
- A friendly mapping from markitdown's internal exception types
  (FailedConversionAttempt, MissingDependencyException,
  UnsupportedFormatException, FileConversionException) to user-readable
  strings, including the `pip install markitdown[xxx]` hint for missing
  dependencies.

The service is **synchronous from the caller's perspective**: `submit()`
queues jobs and returns immediately. Callbacks fire from worker threads;
the Flet UI layer is responsible for dispatching them back to the main
event loop via `page.run_task(...)`.
"""

from __future__ import annotations

import logging
import re
import shutil
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
import threading

from markitdown import MarkItDown  # type: ignore[import-untyped]
from markitdown._exceptions import (  # type: ignore[import-untyped]
    FileConversionException,
    MissingDependencyException,
    UnsupportedFormatException,
)

from ..models.job import ConversionJob, JobStatus
from .settings_service import SettingsService


logger = logging.getLogger(__name__)

# Cap concurrent conversions to 2. Cloud APIs (CU, DocIntel) can be
# expensive to call in parallel; local converters (text, docx) are CPU-bound
# but each is fast. 2 strikes a reasonable balance.
_MAX_WORKERS = 2


# --- Callback type aliases -------------------------------------------------

ProgressCb = Callable[[str, float], None]   # (job_id, progress 0..1)
DoneCb = Callable[[ConversionJob], None]    # success terminal
ErrorCb = Callable[[ConversionJob, str, str | None], None]  # (job, message, install_hint)


# --- Public DTO returned to the UI on completion ---------------------------


@dataclass
class _ErrorEnvelope:
    """Internal: an error with the user-facing message + optional pip hint."""
    message: str
    install_hint: str | None = None


# --- The service -----------------------------------------------------------


class ConverterService:
    """Submit conversion jobs, get callbacks as they progress."""

    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings
        self._executor = ThreadPoolExecutor(
            max_workers=_MAX_WORKERS, thread_name_prefix="md-converter"
        )
        self._cancel_events: dict[str, threading.Event] = {}
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()

    # --- Lifecycle -------------------------------------------------------

    def shutdown(self, wait: bool = False) -> None:
        """Stop accepting new jobs. Called on app exit."""
        self.cancel_all()
        self._executor.shutdown(wait=wait, cancel_futures=not wait)

    # --- Submission ------------------------------------------------------

    def submit(
        self,
        jobs: list[ConversionJob],
        on_progress: ProgressCb | None = None,
        on_done: DoneCb | None = None,
        on_error: ErrorCb | None = None,
    ) -> None:
        """Queue a batch of jobs for conversion.

        All callbacks are optional. They are invoked from worker threads.
        The UI layer should marshal back to the main event loop.
        """
        for job in jobs:
            if job.status != JobStatus.PENDING:
                continue  # ignore jobs that are already running / done
            ev = threading.Event()
            with self._lock:
                self._cancel_events[job.id] = ev
            fut = self._executor.submit(
                self._run_one, job, ev, on_progress, on_done, on_error
            )
            with self._lock:
                self._futures[job.id] = fut
            fut.add_done_callback(lambda f, jid=job.id: self._cleanup_future(jid))

    def cancel(self, job_id: str) -> None:
        """Request cancellation. Marks the cancel event; the worker checks
        it at safe points (between jobs) and also before each long step."""
        with self._lock:
            ev = self._cancel_events.get(job_id)
        if ev is not None:
            ev.set()

    def cancel_all(self) -> None:
        with self._lock:
            events = list(self._cancel_events.values())
        for ev in events:
            ev.set()

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            ev = self._cancel_events.get(job_id)
        return ev is not None and ev.is_set()

    # --- Internals -------------------------------------------------------

    def _cleanup_future(self, job_id: str) -> None:
        with self._lock:
            self._cancel_events.pop(job_id, None)
            self._futures.pop(job_id, None)

    def _run_one(
        self,
        job: ConversionJob,
        cancel_event: threading.Event,
        on_progress: ProgressCb | None,
        on_done: DoneCb | None,
        on_error: ErrorCb | None,
    ) -> None:
        """Worker entry point. Converts one file end-to-end."""
        from datetime import datetime

        if cancel_event.is_set():
            self._mark_cancelled(job)
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        self._emit_progress(on_progress, job, 0.0)

        try:
            md = self._settings.build_markitdown()
        except Exception as exc:  # config / cloud client setup failed
            err = self._envelope(exc, "构建转换器失败")
            self._finish_failed(job, err, on_error)
            return

        if cancel_event.is_set():
            self._mark_cancelled(job)
            return

        try:
            # markitdown is sync + blocking; we cannot interrupt it mid-call,
            # so the cancellation check happens only before/after.
            result = md.convert(str(job.source_path))
        except UnsupportedFormatException as exc:
            err = self._envelope(exc, "无法识别的文件格式")
            self._finish_failed(job, err, on_error)
            return
        except FileConversionException as exc:
            err = self._envelope(exc, self._summarize_attempts(exc))
            self._finish_failed(job, err, on_error)
            return
        except MissingDependencyException as exc:
            err = _ErrorEnvelope(
                message="缺少依赖",
                install_hint=_extract_pip_hint(exc),
            )
            self._finish_failed(job, err, on_error)
            return
        except Exception as exc:
            err = self._envelope(exc, "转换失败")
            self._finish_failed(job, err, on_error)
            return

        if cancel_event.is_set():
            self._mark_cancelled(job)
            return

        # --- Empty-result check: surfaces a friendly diagnostic for image /
        # audio (and similar formats) where conversion "succeeded" but
        # produced no markdown because required system tools (exiftool,
        # ffmpeg) or an LLM client were missing.
        if not result.markdown or not result.markdown.strip():
            diagnostic = _diagnose_empty(job.source_path, kwargs)
            err = _ErrorEnvelope(message=diagnostic)
            self._finish_failed(job, err, on_error)
            return

        # --- Write output file ---
        try:
            self._write_output(job, result.markdown)
        except OSError as exc:
            err = self._envelope(exc, f"无法写入输出文件: {job.output_path}")
            self._finish_failed(job, err, on_error)
            return

        # --- Success ---
        job.status = JobStatus.DONE
        job.markdown = result.markdown
        job.progress = 1.0
        job.finished_at = datetime.now()
        self._emit_progress(on_progress, job, 1.0)
        if on_done is not None:
            try:
                on_done(job)
            except Exception:
                logger.exception("on_done callback raised")

    def _write_output(self, job: ConversionJob, markdown: str) -> None:
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        job.output_path.write_text(markdown, encoding="utf-8")

    def _mark_cancelled(self, job: ConversionJob) -> None:
        from datetime import datetime

        job.status = JobStatus.CANCELLED
        job.finished_at = datetime.now()
        # No callback for cancellation; the UI infers from status.

    def _finish_failed(
        self,
        job: ConversionJob,
        err: _ErrorEnvelope,
        on_error: ErrorCb | None,
    ) -> None:
        from datetime import datetime

        job.status = JobStatus.FAILED
        job.error = err.message
        job.error_install_hint = err.install_hint
        job.finished_at = datetime.now()
        if on_error is not None:
            try:
                on_error(job, err.message, err.install_hint)
            except Exception:
                logger.exception("on_error callback raised")

    def _emit_progress(
        self, cb: ProgressCb | None, job: ConversionJob, value: float
    ) -> None:
        job.progress = value
        if cb is not None:
            try:
                cb(job.id, value)
            except Exception:
                logger.exception("on_progress callback raised")

    @staticmethod
    def _envelope(exc: BaseException, default_msg: str) -> _ErrorEnvelope:
        msg = str(exc).strip() or default_msg
        return _ErrorEnvelope(message=msg)

    @staticmethod
    def _summarize_attempts(exc: FileConversionException) -> str:
        """Build a user-readable summary of the converter attempts."""
        if not exc.attempts:
            return "所有转换器都未接受此文件"
        # Use the *last* error message (most recent attempt). In practice
        # that's usually the most informative.
        last = exc.attempts[-1]
        last_exc = last.exc_info[1] if last.exc_info else None
        last_msg = str(last_exc).strip() if last_exc else "(无错误消息)"
        return f"转换失败: {last_msg}"


# --- Helpers ---------------------------------------------------------------


_PIP_HINT_RE = re.compile(r"`pip install markitdown(?:\[[^\]]+\])?`")

# File extensions that the markitdown core supports only when extra
# **system tools** (exiftool / ffmpeg) or an **LLM client** are present.
# When the result is empty, we look at the extension to explain *why*.
_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".mp4"}


def _extract_pip_hint(exc: BaseException) -> str | None:
    """Find a `pip install markitdown[xxx]` hint in the exception message."""
    msg = str(exc)
    match = _PIP_HINT_RE.search(msg)
    if match:
        return match.group(0).strip("`")
    return None


def _diagnose_empty(source_path: Path, kwargs_used: dict) -> str:
    """Build a friendly explanation when a converter returned empty markdown.

    The markitdown core's `convert()` returns success even for an image
    that produced no EXIF metadata, or an audio file whose transcript is
    empty — there is no exception to catch. The user is left staring at
    a 0-byte .md file. We map the empty result to a concrete "you need
    X / Y" message based on the file type and what's actually available
    on the host.
    """
    ext = source_path.suffix.lower()

    if ext in _IMAGE_EXTS:
        missing: list[str] = []
        if not shutil.which("exiftool"):
            missing.append("exiftool(winget install exiftool)")
        if not kwargs_used.get("llm_client"):
            missing.append("LLM 客户端(在「设置」页配置,用于生成图片描述)")
        if missing:
            return "图片未提取到内容。需要安装或配置: " + "、".join(missing)
        # Both present — exiftool + LLM are there but the image still
        # produced no output (e.g. the image has no EXIF tags and the
        # LLM returned an empty completion).
        return "图片已处理但未生成内容(文件可能没有 EXIF 元数据,且 LLM 未返回描述)"

    if ext in _AUDIO_EXTS:
        missing = []
        if not shutil.which("ffmpeg"):
            missing.append("ffmpeg(winget install ffmpeg)")
        # SpeechRecognition uses Google Web Speech API by default, which
        # needs internet. We can't easily probe connectivity here, but
        # mention it so users have a hint.
        return (
            "音频未提取到内容。可能原因: "
            + ("、".join(missing) + "、" if missing else "")
            + "网络不可达(SpeechRecognition 默认调用 Google Web Speech API)"
        )

    return "未提取到内容(源文件可能为空或格式不被支持)"


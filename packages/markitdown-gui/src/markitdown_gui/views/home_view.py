"""Home view: file drop / browse, conversion queue, preview.

Owns the local state (job list + selected job) and glues the Flet UI
to the ConverterService. All converter callbacks are dispatched back
onto the Flet page via thread-safe `page.update()`.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from pathlib import Path
from typing import ClassVar

import flet as ft

from ..components.drop_zone import drop_zone
from ..components.file_list import file_list
from ..components.preview_panel import preview_panel
from ..constants import SUPPORTED_EXTENSIONS, is_supported
from ..i18n import T
from ..models.job import ConversionJob, JobStatus
from ..services.converter_service import ConverterService
from ..services.settings_service import SettingsService


logger = logging.getLogger(__name__)


class HomeView:
    """A class so we can hold mutable state (jobs, selected) across rebuilds."""

    def __init__(self, page: ft.Page, settings: SettingsService) -> None:
        self.page = page
        self.settings = settings
        self.converter = ConverterService(settings)
        self.jobs: list[ConversionJob] = []
        self.selected_job_id: str | None = None
        # Root container we hand back to app.py; rebuilt on every refresh.
        self._root: ft.Container | None = None
        # FilePicker for the click-to-browse path.
        self._file_picker = ft.FilePicker(on_result=self._on_files_picked)
        page.overlay.append(self._file_picker)
        # Try to enable OS-level drag-and-drop; ignored if the host doesn't support it.
        try:
            page.on_file_drop = self._on_page_file_drop
        except Exception:
            logger.info("OS drag-and-drop not enabled; click-only browsing.")

    # --- Public API ------------------------------------------------------

    def build(self) -> ft.Control:
        """Return the root control for the home view."""
        self._root = ft.Container(
            content=self._build_content(),
            expand=True,
        )
        return self._root

    def shutdown(self) -> None:
        """Called on app exit."""
        self.converter.shutdown(wait=False)

    # --- Content builders ------------------------------------------------

    def _build_content(self) -> ft.Control:
        # Top half: drop zone + task list
        top_half = ft.Column(
            [
                self._build_top_bar(),
                ft.Container(padding=8),
                ft.Container(content=drop_zone(self._on_pick_files_click), padding=ft.padding.symmetric(horizontal=16)),
                ft.Container(padding=8),
                ft.Container(
                    content=file_list(
                        self.jobs,
                        on_preview=self._on_preview,
                        on_open_folder=self._on_open_folder,
                        on_cancel=self._on_cancel,
                        on_retry=self._on_retry,
                        on_delete=self._on_delete,
                        on_copy_pip=self._on_copy_pip,
                    ),
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=8,
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        )

        # Bottom: preview panel (visible if any job is selected & done)
        preview = preview_panel(
            self._get_selected_job(),
            on_copy=self._on_copy_to_clipboard,
            on_save_as=self._on_save_as,
        )

        return ft.Column(
            [
                top_half,
                ft.Container(
                    content=preview,
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=8,
                    height=240,
                ),
            ],
            expand=True,
            spacing=8,
        )

    def _build_top_bar(self) -> ft.Control:
        count = len(self.jobs)
        has_pending = any(j.status == JobStatus.PENDING for j in self.jobs)
        has_running = any(j.status == JobStatus.RUNNING for j in self.jobs)
        has_completed = any(
            j.status in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED)
            for j in self.jobs
        )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        T.home_tasks_count(count) if count else T.home_tasks_title_pending,
                        size=16,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Container(expand=True),
                    ft.TextButton(
                        T.home_action_clear_completed,
                        icon=ft.Icons.CLEANING_SERVICES,
                        disabled=not has_completed,
                        on_click=lambda _: self._on_clear_completed(),
                    ),
                    ft.TextButton(
                        T.home_action_clear,
                        icon=ft.Icons.CLEAR_ALL,
                        disabled=count == 0,
                        on_click=lambda _: self._on_clear(),
                    ),
                    ft.FilledButton(
                        T.home_action_convert,
                        icon=ft.Icons.PLAY_ARROW,
                        disabled=not has_pending,
                        on_click=lambda _: self._on_start(),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16),
        )

    # --- File pick / drop handlers ---------------------------------------

    def _on_pick_files_click(self) -> None:
        # Flet expects extensions without the leading dot in `allowed_extensions`.
        exts_no_dot = [ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS]
        self._file_picker.pick_files(
            allow_multiple=True,
            allowed_extensions=exts_no_dot,
        )

    def _on_files_picked(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        for f in e.files:
            self._add_file(Path(f.path))

    def _on_page_file_drop(self, e) -> None:
        """Called by Flet when the user drops files onto the page.

        `e.files` is a list of objects with a `.path` attribute. We tolerate
        the exact shape across Flet versions by getattr.
        """
        for f in getattr(e, "files", []) or []:
            p = getattr(f, "path", None)
            if p:
                self._add_file(Path(p))

    # --- Job queue operations --------------------------------------------

    def _add_file(self, source_path: Path) -> None:
        # Reject unsupported extensions (image / audio / etc.). The file
        # picker's `allowed_extensions` already filters the dialog, but
        # drag-and-drop bypasses that, so we enforce here too.
        ext = source_path.suffix.lower()
        if not is_supported(source_path.name):
            self._show_snackbar(T.home_unsupported_file(ext or "(无扩展名)"))
            return
        # Skip duplicates already in the queue (compare absolute paths).
        abs_path = source_path.resolve()
        if any(j.source_path.resolve() == abs_path for j in self.jobs):
            return
        output_dir = self._resolve_output_dir(source_path)
        output_path = output_dir / (source_path.stem + ".md")
        self.jobs.append(ConversionJob(source_path=abs_path, output_path=output_path))
        self._refresh()

    def _resolve_output_dir(self, source_path: Path) -> Path:
        cfg = self.settings.get_config()
        if cfg.default_output_dir:
            return Path(cfg.default_output_dir)
        return source_path.parent

    def _on_clear(self) -> None:
        # Only clear jobs that aren't running.
        self.jobs = [j for j in self.jobs if j.status == JobStatus.RUNNING]
        if self.selected_job_id and not any(j.id == self.selected_job_id for j in self.jobs):
            self.selected_job_id = None
        self._refresh()

    def _on_clear_completed(self) -> None:
        """Remove all jobs in terminal states (DONE / FAILED / CANCELLED).

        PENDING jobs stay queued; RUNNING jobs are left to finish.
        """
        self.jobs = [
            j
            for j in self.jobs
            if j.status not in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED)
        ]
        if self.selected_job_id and not any(j.id == self.selected_job_id for j in self.jobs):
            self.selected_job_id = None
        self._refresh()

    def _on_delete(self, job: ConversionJob) -> None:
        """Remove a single job from the queue.

        Allowed in every state EXCEPT RUNNING. The job card hides this
        button while a job is running, so reaching here for a RUNNING job
        would be a UI bug — guard anyway just in case.
        """
        if job.status == JobStatus.RUNNING:
            return
        # If it's PENDING, the worker may not have started yet — set the
        # cancel flag so any in-flight worker exits as CANCELLED instead
        # of running. For terminal states this is a no-op.
        self.converter.cancel(job.id)
        self.jobs = [j for j in self.jobs if j.id != job.id]
        if self.selected_job_id == job.id:
            self.selected_job_id = None
        self._refresh()

    def _on_start(self) -> None:
        pending = [j for j in self.jobs if j.status == JobStatus.PENDING]
        if not pending:
            return
        self.converter.submit(
            pending,
            on_progress=self._on_job_progress,
            on_done=self._on_job_done,
            on_error=self._on_job_error,
        )
        self._refresh()

    # --- Per-job actions -------------------------------------------------

    def _on_preview(self, job: ConversionJob) -> None:
        self.selected_job_id = job.id
        self._refresh()

    def _on_open_folder(self, job: ConversionJob) -> None:
        """Open the output file's parent folder in the OS file manager."""
        folder = job.output_path.parent
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", str(folder)])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            logger.warning("Failed to open folder %s: %s", folder, exc)

    def _on_cancel(self, job: ConversionJob) -> None:
        self.converter.cancel(job.id)
        # Worker will set status=CANCELLED; refresh optimistically for UX.
        self._refresh()

    def _on_retry(self, job: ConversionJob) -> None:
        # Reset and re-submit.
        job.status = JobStatus.PENDING
        job.progress = 0.0
        job.error = None
        job.error_install_hint = None
        job.markdown = None
        job.started_at = None
        job.finished_at = None
        self._refresh()
        self.converter.submit(
            [job],
            on_progress=self._on_job_progress,
            on_done=self._on_job_done,
            on_error=self._on_job_error,
        )
        self._refresh()

    def _on_copy_pip(self, job: ConversionJob) -> None:
        if not job.error_install_hint:
            return
        self.page.set_clipboard(job.error_install_hint)
        self._show_snackbar(T.info_copied)

    def _on_copy_to_clipboard(self, text: str) -> None:
        self.page.set_clipboard(text)
        self._show_snackbar(T.info_copied)

    def _on_save_as(self, markdown_text: str, suggested_name: str) -> None:
        """Open a save-file dialog with the suggested .md filename."""
        self._pending_save_text = markdown_text
        # FilePicker.save_file is async-ish; stash the text on the page.
        self._file_picker.save_file(
            dialog_title=T.home_action_save_as,
            file_name=suggested_name.rsplit(".", 1)[0] + ".md" if "." in suggested_name else suggested_name + ".md",
        )
        # The result will arrive in on_result — but we overwrote it for pick.
        # So handle save via a one-shot callback swap.
        self._file_picker.on_result = self._on_save_result

    _pending_save_text: ClassVar[str | None] = None

    def _on_save_result(self, e: ft.FilePickerResultEvent) -> None:
        # Restore the pick callback for subsequent use.
        self._file_picker.on_result = self._on_files_picked
        if not e.path or not self._pending_save_text:
            return
        try:
            Path(e.path).write_text(self._pending_save_text, encoding="utf-8")
            self._show_snackbar(T.info_saved_to(e.path))
        except OSError as exc:
            self._show_snackbar(f"保存失败: {exc}")
        finally:
            self._pending_save_text = None

    # --- Callbacks from worker threads (thread-safe via page.update) -----

    def _on_job_progress(self, job_id: str, progress: float) -> None:
        # Worker thread. Find the job and update progress.
        for j in self.jobs:
            if j.id == job_id:
                j.progress = progress
                break
        self._refresh()

    def _on_job_done(self, job: ConversionJob) -> None:
        # Worker thread. The job object is mutated in-place; just refresh.
        self._refresh()

    def _on_job_error(self, job: ConversionJob, message: str, install_hint: str | None) -> None:
        # Worker thread. Job object is mutated; just refresh.
        self._refresh()

    # --- Helpers ---------------------------------------------------------

    def _get_selected_job(self) -> ConversionJob | None:
        if self.selected_job_id is None:
            return None
        for j in self.jobs:
            if j.id == self.selected_job_id:
                return j
        return None

    def _show_snackbar(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(content=ft.Text(message), open=True)
        self.page.update()

    def _refresh(self) -> None:
        """Rebuild the root control with current state.

        Called from the UI thread AND from worker threads (Flet's
        `page.update()` is thread-safe and schedules the actual redraw
        on the main loop).
        """
        if self._root is None:
            return
        self._root.content = self._build_content()
        try:
            self.page.update()
        except Exception:
            # Page might be torn down during shutdown; ignore.
            pass

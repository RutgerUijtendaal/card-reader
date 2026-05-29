from __future__ import annotations

from card_reader_core.models import ImportJob, ImportJobItem, ImportJobStatus, now_utc


def mark_job_running(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.running)


def mark_job_queued(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.queued)


def mark_job_complete(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.completed)


def mark_job_failed(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.failed)


def mark_job_canceling(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.canceling)


def mark_job_cancelled(job: ImportJob) -> None:
    from .queries import fetch_items_for_job

    job.status = ImportJobStatus.cancelled
    job.processed_items = count_terminal_items(fetch_items_for_job(job.id))
    job.updated_at = now_utc()
    job.save(update_fields=["status", "processed_items", "updated_at"])


def bump_job_processed(job: ImportJob) -> None:
    job.processed_items += 1
    job.updated_at = now_utc()
    job.save(update_fields=["processed_items", "updated_at"])


def mark_job_item_failed(item: ImportJobItem, error_message: str) -> None:
    item.status = ImportJobStatus.failed
    item.error_message = error_message[:2000]
    item.updated_at = now_utc()
    item.save(update_fields=["status", "error_message", "updated_at"])


def mark_job_item_running(item: ImportJobItem) -> None:
    item.status = ImportJobStatus.running
    item.error_message = None
    item.warning_code = None
    item.warning_message = None
    item.updated_at = now_utc()
    item.save(update_fields=["status", "error_message", "warning_code", "warning_message", "updated_at"])


def mark_job_item_cancelled(item: ImportJobItem) -> None:
    item.status = ImportJobStatus.cancelled
    item.error_message = None
    item.updated_at = now_utc()
    item.save(update_fields=["status", "error_message", "updated_at"])


def count_terminal_items(items: list[ImportJobItem]) -> int:
    terminal_statuses = {ImportJobStatus.completed, ImportJobStatus.failed, ImportJobStatus.cancelled}
    return sum(1 for item in items if item.status in terminal_statuses)


def _set_job_status(job: ImportJob, status: ImportJobStatus) -> None:
    job.status = status
    job.updated_at = now_utc()
    job.save(update_fields=["status", "updated_at"])

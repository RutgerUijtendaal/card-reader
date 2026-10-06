from __future__ import annotations

from django.db import transaction
from django.db.models import F

from card_reader_core.models import ImportJob, ImportJobItem, ImportJobStatus, now_utc

MAX_IMPORT_ITEM_ATTEMPTS = 3
INTERRUPTED_ATTEMPTS_ERROR = (
    f"Parser processing was interrupted repeatedly; stopped after {MAX_IMPORT_ITEM_ATTEMPTS} attempts. "
    "Submit a new import or reparse to try again."
)


def finalize_import_job(job: ImportJob) -> None:
    """Reconcile progress and outcome from durable items across worker restarts."""
    from .queries import fetch_items_for_job

    with transaction.atomic():
        current = ImportJob.objects.select_for_update().filter(id=job.id).first()
        if current is None:
            return
        if current.status in {ImportJobStatus.canceling, ImportJobStatus.cancelled}:
            mark_job_cancelled(current)
            return
        items = fetch_items_for_job(job.id)
        job.processed_items = count_terminal_items(items)
        if any(item.status == ImportJobStatus.running for item in items):
            job.status = ImportJobStatus.running
        elif any(item.status == ImportJobStatus.queued for item in items):
            job.status = ImportJobStatus.queued
        elif any(item.status == ImportJobStatus.failed for item in items):
            job.status = ImportJobStatus.failed
        else:
            job.status = ImportJobStatus.completed
        job.updated_at = now_utc()
        job.save(update_fields=["status", "processed_items", "updated_at"])


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


def mark_job_item_running(item: ImportJobItem) -> bool:
    """Commit the attempt before parsing, including when parsing kills the process."""
    with transaction.atomic():
        queued = ImportJobItem.objects.filter(id=item.id, status=ImportJobStatus.queued)
        claimed = queued.filter(attempt_count__lt=MAX_IMPORT_ITEM_ATTEMPTS).update(
            status=ImportJobStatus.running,
            attempt_count=F("attempt_count") + 1,
            error_message=None,
            updated_at=now_utc(),
        )
        if not claimed:
            queued.filter(attempt_count__gte=MAX_IMPORT_ITEM_ATTEMPTS).update(
                status=ImportJobStatus.failed,
                error_message=INTERRUPTED_ATTEMPTS_ERROR,
                updated_at=now_utc(),
            )
    item.refresh_from_db(fields=["status", "attempt_count", "error_message", "updated_at"])
    return bool(claimed)


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

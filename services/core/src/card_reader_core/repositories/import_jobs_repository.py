from __future__ import annotations

from pathlib import Path

from django.db import transaction

from ..models import ImportJob, ImportJobItem, ImportJobStatus, now_utc
from ..storage import relativize_storage_path, resolve_storage_path

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def collect_supported_files(source_path: Path) -> list[Path]:
    source_path = resolve_storage_path(source_path)
    if source_path.is_file():
        return [source_path] if source_path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES else []
    if not source_path.is_dir():
        return []
    return sorted(
        path
        for path in source_path.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    )


def list_import_jobs() -> list[ImportJob]:
    return list(ImportJob.objects.order_by("-created_at"))


def create_import_job(
    *,
    source_path: Path,
    template_id: str,
    options: dict[str, object],
) -> ImportJob:
    files = collect_supported_files(source_path)
    return create_import_job_with_files(
        source_path=source_path,
        template_id=template_id,
        options=options,
        files=files,
    )


def create_import_job_with_files(
    *,
    source_path: Path,
    template_id: str,
    options: dict[str, object],
    files: list[Path],
) -> ImportJob:
    with transaction.atomic():
        job = ImportJob.objects.create(
            source_path=relativize_storage_path(
                source_path,
                default_root="uploads",
                preserve_unmatched_absolute=True,
            ),
            template_id=template_id,
            options_json=options,
            total_items=len(files),
            processed_items=0,
        )
        ImportJobItem.objects.bulk_create(
            [
                ImportJobItem(
                    job=job,
                    source_file=relativize_storage_path(
                        image_file,
                        default_root="uploads",
                        preserve_unmatched_absolute=True,
                    ),
                    status=ImportJobStatus.queued,
                )
                for image_file in files
            ]
        )
    return job


def fetch_job(job_id: str) -> ImportJob | None:
    return ImportJob.objects.filter(id=job_id).first()


def fetch_items_for_job(job_id: str) -> list[ImportJobItem]:
    return list(ImportJobItem.objects.filter(job_id=job_id).order_by("created_at"))
def get_next_queued_job() -> ImportJob | None:
    return ImportJob.objects.filter(status=ImportJobStatus.queued).order_by("created_at").first()


def mark_job_running(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.running)


def mark_job_queued(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.queued)


def mark_job_complete(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.completed)


def mark_job_failed(job: ImportJob) -> None:
    _set_job_status(job, ImportJobStatus.failed)


def bump_job_processed(job: ImportJob) -> None:
    job.processed_items += 1
    job.updated_at = now_utc()
    job.save(update_fields=["processed_items", "updated_at"])


def mark_job_item_failed(item: ImportJobItem, error_message: str) -> None:
    item.status = ImportJobStatus.failed
    item.error_message = error_message[:2000]
    item.updated_at = now_utc()
    item.save(update_fields=["status", "error_message", "updated_at"])


def requeue_running_import_jobs() -> tuple[int, int]:
    jobs = list(ImportJob.objects.filter(status=ImportJobStatus.running))
    recovered_item_count = 0
    processed_statuses = {ImportJobStatus.completed, ImportJobStatus.failed}

    for job in jobs:
        items = list(ImportJobItem.objects.filter(job_id=job.id))
        for item in items:
            if item.status != ImportJobStatus.running:
                continue
            item.status = ImportJobStatus.queued
            item.error_message = None
            item.updated_at = now_utc()
            item.save(update_fields=["status", "error_message", "updated_at"])
            recovered_item_count += 1

        job.status = ImportJobStatus.queued
        job.processed_items = sum(1 for item in items if item.status in processed_statuses)
        job.updated_at = now_utc()
        job.save(update_fields=["status", "processed_items", "updated_at"])

    return len(jobs), recovered_item_count


def _set_job_status(job: ImportJob, status: ImportJobStatus) -> None:
    job.status = status
    job.updated_at = now_utc()
    job.save(update_fields=["status", "updated_at"])

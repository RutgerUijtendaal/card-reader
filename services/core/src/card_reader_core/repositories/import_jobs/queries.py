from __future__ import annotations

from card_reader_core.models import ImportJob, ImportJobItem, ImportJobStatus


def list_import_jobs() -> list[ImportJob]:
    return list(ImportJob.objects.select_related("content_version").order_by("-created_at"))


def fetch_job(job_id: str) -> ImportJob | None:
    return ImportJob.objects.select_related("content_version").filter(id=job_id).first()


def fetch_items_for_job(job_id: str) -> list[ImportJobItem]:
    return list(
        ImportJobItem.objects.filter(job_id=job_id)
        .select_related("job__content_version", "target_card", "target_card_version")
        .order_by("created_at")
    )


def get_next_queued_job() -> ImportJob | None:
    return (
        ImportJob.objects.select_related("content_version")
        .filter(status=ImportJobStatus.queued)
        .order_by("created_at")
        .first()
    )

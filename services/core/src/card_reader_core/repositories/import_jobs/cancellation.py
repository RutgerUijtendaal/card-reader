from __future__ import annotations

from django.db import transaction

from card_reader_core.models import ImportJob, ImportJobItem, ImportJobStatus, now_utc

from .queries import fetch_items_for_job
from .status import count_terminal_items, mark_job_cancelled, mark_job_item_cancelled


def cancel_import_job(job_id: str) -> ImportJob | None:
    with transaction.atomic():
        job = ImportJob.objects.select_for_update().filter(id=job_id).first()
        if job is None:
            return None
        if job.status in {ImportJobStatus.completed, ImportJobStatus.failed, ImportJobStatus.cancelled}:
            return job

        items = list(ImportJobItem.objects.select_for_update().filter(job_id=job.id))
        for item in items:
            if item.status == ImportJobStatus.queued:
                mark_job_item_cancelled(item)

        terminal_status = count_terminal_items(items)
        job.processed_items = terminal_status
        job.updated_at = now_utc()
        if job.status == ImportJobStatus.running:
            job.status = ImportJobStatus.canceling
            job.save(update_fields=["status", "processed_items", "updated_at"])
            return job

        for item in items:
            if item.status == ImportJobStatus.running:
                mark_job_item_cancelled(item)

        job.status = ImportJobStatus.cancelled
        job.processed_items = count_terminal_items(fetch_items_for_job(job.id))
        job.save(update_fields=["status", "processed_items", "updated_at"])
        return job


def requeue_running_import_jobs() -> tuple[int, int]:
    jobs = list(ImportJob.objects.filter(status__in=[ImportJobStatus.running, ImportJobStatus.canceling]))
    recovered_item_count = 0

    for job in jobs:
        items = list(ImportJobItem.objects.filter(job_id=job.id))
        if job.status == ImportJobStatus.canceling:
            for item in items:
                if item.status in {ImportJobStatus.queued, ImportJobStatus.running}:
                    mark_job_item_cancelled(item)
                    recovered_item_count += 1
            mark_job_cancelled(job)
            continue

        for item in items:
            if item.status != ImportJobStatus.running:
                continue
            item.status = ImportJobStatus.queued
            item.error_message = None
            item.updated_at = now_utc()
            item.save(update_fields=["status", "error_message", "updated_at"])
            recovered_item_count += 1

        job.status = ImportJobStatus.queued
        job.processed_items = count_terminal_items(items)
        job.updated_at = now_utc()
        job.save(update_fields=["status", "processed_items", "updated_at"])

    return len(jobs), recovered_item_count

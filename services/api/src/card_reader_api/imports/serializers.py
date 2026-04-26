from __future__ import annotations

from card_reader_core.models import ImportJob, ImportJobItem


def import_job_payload(job: ImportJob) -> dict[str, object]:
    return {
        "id": job.id,
        "source_path": job.source_path,
        "template_id": job.template_id,
        "status": job.status,
        "total_items": job.total_items,
        "processed_items": job.processed_items,
    }


def import_detail_payload(job: ImportJob, items: list[ImportJobItem]) -> dict[str, object]:
    return {
        **import_job_payload(job),
        "items": [
            {
                "id": item.id,
                "source_file": item.source_file,
                "status": item.status,
                "error_message": item.error_message,
            }
            for item in items
        ],
    }

from __future__ import annotations

from models import ImportJob, ImportJobItem
from schemas import ImportJobDetailResponse, ImportJobItemResponse, ImportJobResponse


def to_import_job_response(job: ImportJob) -> ImportJobResponse:
    return ImportJobResponse(
        id=job.id,
        source_path=job.source_path,
        template_id=job.template_id,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
    )


def to_import_job_item_response(item: ImportJobItem) -> ImportJobItemResponse:
    return ImportJobItemResponse(
        id=item.id,
        source_file=item.source_file,
        status=item.status,
        error_message=item.error_message,
    )


def to_import_job_detail_response(job: ImportJob, items: list[ImportJobItem]) -> ImportJobDetailResponse:
    return ImportJobDetailResponse(
        id=job.id,
        source_path=job.source_path,
        template_id=job.template_id,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
        items=[to_import_job_item_response(item) for item in items],
    )

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from django.db import transaction

from card_reader_core.models import ContentVersion, ImportJob, ImportJobItem, ImportJobStatus
from card_reader_core.repositories.templates import get_template_by_key
from card_reader_core.storage import relativize_storage_path

from .files import collect_supported_files
from .types import ImportJobItemTarget


def create_import_job(
    *,
    source_path: Path,
    template_id: str,
    options: dict[str, object],
    content_version: ContentVersion | None = None,
    item_targets: Sequence[ImportJobItemTarget | None] | None = None,
) -> ImportJob:
    files = collect_supported_files(source_path)
    return create_import_job_with_files(
        source_path=source_path,
        template_id=template_id,
        options=options,
        content_version=content_version,
        files=files,
        item_targets=item_targets,
    )


def create_import_job_with_files(
    *,
    source_path: Path,
    template_id: str,
    options: dict[str, object],
    files: list[Path],
    content_version: ContentVersion | None = None,
    item_targets: Sequence[ImportJobItemTarget | None] | None = None,
) -> ImportJob:
    normalized_targets = list(item_targets) if item_targets is not None else [None] * len(files)
    if len(normalized_targets) != len(files):
        raise ValueError("item_targets length must match files length")
    template = get_template_by_key(key=template_id)
    if template is None:
        raise ValueError(f"Unknown template_id '{template_id}'")

    with transaction.atomic():
        job = ImportJob.objects.create(
            source_path=relativize_storage_path(
                source_path,
                default_root="uploads",
                preserve_unmatched_absolute=True,
            ),
            template=template,
            content_version=content_version,
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
                    target_card_id=target.card_id if target is not None else None,
                    target_card_version_id=target.card_version_id if target is not None else None,
                    status=ImportJobStatus.queued,
                )
                for image_file, target in zip(files, normalized_targets, strict=True)
            ]
        )
    return job

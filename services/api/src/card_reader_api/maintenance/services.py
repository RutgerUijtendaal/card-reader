from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.core.management import call_command

from card_reader_core.repositories.cards_repository import list_latest_card_version_reparse_sources
from card_reader_core.repositories.import_jobs_repository import ImportJobItemTarget, create_import_job_with_files
from card_reader_core.settings import settings


@dataclass(slots=True)
class MaintenanceResult:
    message: str
    removed_paths: list[str]


class MaintenanceService:
    def backfill_metadata_suggestions(self) -> MaintenanceResult:
        call_command("backfill_metadata_suggestions", verbosity=0)
        return MaintenanceResult(
            message="Metadata suggestions backfill completed.",
            removed_paths=[],
        )

    def queue_reparse_latest_versions(self) -> MaintenanceResult:
        grouped_files: dict[str, list[Path]] = {}

        sources = list_latest_card_version_reparse_sources()
        if not sources:
            return MaintenanceResult(
                message="No latest card versions found to reparse.",
                removed_paths=[],
            )

        item_count = 0
        for source in sources:
            grouped_files.setdefault(source.template_id, []).append(source.image_path)
            item_count += 1

        if not grouped_files:
            return MaintenanceResult(
                message="No readable latest card images found to queue for reparse.",
                removed_paths=[],
            )

        job_count = 0
        for template_id, files in grouped_files.items():
            targets = [
                ImportJobItemTarget(card_id=source.card_id, card_version_id=source.card_version_id)
                for source in sources
                if source.template_id == template_id
            ]
            create_import_job_with_files(
                source_path=settings.storage_root_dir / "maintenance" / f"reparse-latest-{template_id}",
                template_id=template_id,
                options={"reparse_existing": True},
                files=files,
                item_targets=targets,
            )
            job_count += 1

        return MaintenanceResult(
            message=(
                f"Queued {job_count} reparse job{'s' if job_count != 1 else ''} "
                f"for {item_count} latest card image{'s' if item_count != 1 else ''}."
            ),
            removed_paths=[],
        )

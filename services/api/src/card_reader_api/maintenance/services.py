from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.core.management import call_command

from card_reader_api.cards.serializers import CardFilterParams
from card_reader_core.repositories.cards import (
    LatestCardVersionReparseSource,
    list_filtered_latest_card_version_reparse_sources,
    list_latest_card_version_reparse_sources,
)
from card_reader_core.repositories.import_jobs import ImportJobItemTarget, create_import_job_with_files
from card_reader_core.config.settings import settings


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
        sources = list_latest_card_version_reparse_sources()
        return self._queue_reparse_sources(
            sources,
            empty_message="No latest card versions found to reparse.",
            unreadable_message="No readable latest card images found to queue for reparse.",
            source_name_prefix="reparse-latest",
            message_suffix=".",
        )

    def queue_reparse_latest_versions_by_filters(self, *, filters: CardFilterParams) -> MaintenanceResult:
        sources = list_filtered_latest_card_version_reparse_sources(**filters)
        return self._queue_reparse_sources(
            sources,
            empty_message="No latest card versions matched the selected filters.",
            unreadable_message="No readable latest card images matched the selected filters.",
            source_name_prefix="reparse-filtered",
            message_suffix=" matching the selected filters.",
        )

    def _queue_reparse_sources(
        self,
        sources: list[LatestCardVersionReparseSource],
        *,
        empty_message: str,
        unreadable_message: str,
        source_name_prefix: str,
        message_suffix: str,
    ) -> MaintenanceResult:
        grouped_files: dict[str, list[Path]] = {}
        if not sources:
            return MaintenanceResult(message=empty_message, removed_paths=[])

        item_count = 0
        for source in sources:
            template_id = source.template_id
            image_path = source.image_path
            grouped_files.setdefault(template_id, []).append(image_path)
            item_count += 1

        if not grouped_files:
            return MaintenanceResult(message=unreadable_message, removed_paths=[])

        job_count = 0
        for template_id, files in grouped_files.items():
            targets = [
                ImportJobItemTarget(
                    card_id=source.card_id,
                    card_version_id=source.card_version_id,
                )
                for source in sources
                if source.template_id == template_id
            ]
            create_import_job_with_files(
                source_path=settings.storage_root_dir / "maintenance" / f"{source_name_prefix}-{template_id}",
                template_id=template_id,
                options={"reparse_existing": True},
                files=files,
                item_targets=targets,
            )
            job_count += 1

        return MaintenanceResult(
            message=(
                f"Queued {job_count} reparse job{'s' if job_count != 1 else ''} "
                f"for {item_count} latest card image{'s' if item_count != 1 else ''}"
                f"{message_suffix}"
            ),
            removed_paths=[],
        )

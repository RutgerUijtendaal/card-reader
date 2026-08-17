from __future__ import annotations

from dataclasses import dataclass

from django.core.management import call_command

from card_reader_core.repositories.cards import (
    CardFilterParams,
    LatestCardVersionReparseSource,
    list_filtered_latest_card_version_reparse_sources,
    list_latest_card_version_reparse_sources,
)
from card_reader_core.services.cards import CardImageConversionResult, convert_card_images_to_webp
from card_reader_core.services.imports import queue_grouped_reparse_jobs


@dataclass(slots=True)
class MaintenanceResult:
    message: str
    removed_paths: list[str]


@dataclass(slots=True)
class CardImageConversionMaintenanceResult:
    message: str
    removed_paths: list[str]
    conversion: CardImageConversionResult


class MaintenanceService:
    def backfill_metadata_suggestions(self) -> MaintenanceResult:
        call_command("backfill_metadata_suggestions", verbosity=0)
        return MaintenanceResult(
            message="Metadata suggestions backfill completed.",
            removed_paths=[],
        )

    def convert_card_images_to_webp(self) -> CardImageConversionMaintenanceResult:
        conversion = convert_card_images_to_webp()
        return CardImageConversionMaintenanceResult(
            message=conversion.message,
            removed_paths=[],
            conversion=conversion,
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
        if not sources:
            return MaintenanceResult(message=empty_message, removed_paths=[])
        summary = queue_grouped_reparse_jobs(
            sources=sources,
            source_name_prefix=source_name_prefix,
        )
        if summary.item_count == 0:
            return MaintenanceResult(message=unreadable_message, removed_paths=[])

        return MaintenanceResult(
            message=(
                f"Queued {summary.job_count} reparse job{'s' if summary.job_count != 1 else ''} "
                f"for {summary.item_count} latest card image{'s' if summary.item_count != 1 else ''}"
                f"{message_suffix}"
            ),
            removed_paths=[],
        )

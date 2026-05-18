from __future__ import annotations

from typing import Any

from card_reader_core.metadata_matching import KnownMetadataMatcher
from card_reader_core.metadata_suggestions import extract_metadata_ids_and_suggestions, split_middle_text
from django.core.management.base import BaseCommand

from card_reader_core.models import CardVersion
from card_reader_core.repositories.metadata_repository import (
    SuggestionCandidate,
    list_tags,
    list_types,
    replace_card_version_metadata_suggestions,
)


class Command(BaseCommand):
    help = "Backfill tag/type suggestions from latest card version type_line values."

    def handle(self, *args: Any, **options: Any) -> None:
        _ = args
        _ = options
        matcher = KnownMetadataMatcher()
        tags = list_tags()
        types = list_types()
        versions = list(CardVersion.objects.filter(is_latest=True).order_by("updated_at"))

        updated = 0
        for version in versions:
            type_text, tag_text = split_middle_text(version.type_line)
            _, type_drafts = extract_metadata_ids_and_suggestions(
                type_text,
                types,
                kind="type",
                matcher=matcher,
            )
            _, tag_drafts = extract_metadata_ids_and_suggestions(
                tag_text,
                tags,
                kind="tag",
                matcher=matcher,
            )
            replace_card_version_metadata_suggestions(
                card_version_id=version.id,
                kind="type",
                candidates=[suggestion_candidate_from_draft(row) for row in type_drafts],
                parse_result_id=getattr(version, "parse_result_id", None),
            )
            replace_card_version_metadata_suggestions(
                card_version_id=version.id,
                kind="tag",
                candidates=[suggestion_candidate_from_draft(row) for row in tag_drafts],
                parse_result_id=getattr(version, "parse_result_id", None),
            )
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Backfilled metadata suggestions for {updated} latest card versions."))


def suggestion_candidate_from_draft(row: object) -> SuggestionCandidate:
    return SuggestionCandidate(
        display_value=getattr(row, "display_value"),
        normalized_value=getattr(row, "normalized_value"),
        source_text=getattr(row, "source_text"),
        normalized_source_text=getattr(row, "normalized_source_text"),
    )

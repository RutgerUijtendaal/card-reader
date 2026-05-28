from __future__ import annotations

from django.db.models import Count

from card_reader_core.models import (
    CardVersionMetadataSuggestion,
    MetadataSuggestion,
    now_utc,
)

from .types import MetadataSuggestionListRow, SuggestionCandidate


def get_metadata_suggestion(entry_id: str) -> MetadataSuggestion | None:
    return (
        MetadataSuggestion.objects.filter(id=entry_id)
        .select_related("accepted_tag", "accepted_type")
        .first()
    )


def reject_metadata_suggestion(*, suggestion_id: str) -> MetadataSuggestion | None:
    suggestion = get_metadata_suggestion(suggestion_id)
    if suggestion is None:
        return None
    suggestion.status = "rejected"
    suggestion.updated_at = now_utc()
    suggestion.save(update_fields=["status", "updated_at"])
    return suggestion


def get_or_create_metadata_suggestion(
    *,
    kind: str,
    normalized_value: str,
    display_value: str,
) -> MetadataSuggestion:
    suggestion = (
        MetadataSuggestion.objects.filter(kind=kind, normalized_value=normalized_value)
        .select_related("accepted_tag", "accepted_type")
        .first()
    )
    if suggestion is not None:
        if not suggestion.display_value.strip() and display_value.strip():
            suggestion.display_value = display_value
            suggestion.updated_at = now_utc()
            suggestion.save(update_fields=["display_value", "updated_at"])
        return suggestion
    return MetadataSuggestion.objects.create(
        kind=kind,
        normalized_value=normalized_value,
        display_value=display_value,
    )


def replace_card_version_metadata_suggestions(
    *,
    card_version_id: str,
    kind: str,
    candidates: list[SuggestionCandidate],
    parse_result_id: str | None = None,
) -> None:
    CardVersionMetadataSuggestion.objects.filter(
        card_version_id=card_version_id,
        suggestion__kind=kind,
    ).delete()

    seen: set[str] = set()
    rows: list[CardVersionMetadataSuggestion] = []
    for candidate in candidates:
        if candidate.normalized_value in seen:
            continue
        seen.add(candidate.normalized_value)
        suggestion = get_or_create_metadata_suggestion(
            kind=kind,
            normalized_value=candidate.normalized_value,
            display_value=candidate.display_value,
        )
        rows.append(
            CardVersionMetadataSuggestion(
                card_version_id=card_version_id,
                suggestion_id=suggestion.id,
                parse_result_id=parse_result_id,
                source_text=candidate.source_text,
                normalized_source_text=candidate.normalized_source_text,
            )
        )
    CardVersionMetadataSuggestion.objects.bulk_create(rows)


def list_metadata_suggestions(
    *,
    kind: str,
    status: str | None = None,
) -> list[MetadataSuggestionListRow]:
    query = (
        MetadataSuggestion.objects.filter(kind=kind)
        .select_related("accepted_tag", "accepted_type")
        .annotate(
            occurrence_count=Count("card_version_metadata_suggestions", distinct=True)
        )
        .filter(occurrence_count__gt=0)
        .order_by("-occurrence_count", "display_value", "normalized_value")
    )
    if status is not None:
        query = query.filter(status=status)
    return [
        MetadataSuggestionListRow(
            suggestion=row,
            occurrence_count=int(getattr(row, "occurrence_count", 0)),
        )
        for row in query
    ]


def list_card_version_suggestion_occurrences(
    suggestion_id: str,
) -> list[CardVersionMetadataSuggestion]:
    return list(
        CardVersionMetadataSuggestion.objects.filter(suggestion_id=suggestion_id)
        .select_related("card_version__card", "parse_result")
        .prefetch_related("card_version__images")
        .order_by("-created_at")
    )

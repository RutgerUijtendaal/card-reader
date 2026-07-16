from __future__ import annotations

from django.db.models import Count

from card_reader_core.models import Deck, DeckTag, DeckTagKind, DeckTagSuggestion
from card_reader_core.repositories.decks.prefetch import deck_summary_queryset


def list_deck_tags(*, kind: DeckTagKind | None = None) -> list[DeckTag]:
    query = DeckTag.objects.annotate(linked_deck_count=Count("assignments__deck", distinct=True))
    if kind is not None:
        query = query.filter(kind=kind)
    return list(query.order_by("kind", "label", "id"))


def get_deck_tag(tag_id: str) -> DeckTag | None:
    return (
        DeckTag.objects.annotate(linked_deck_count=Count("assignments__deck", distinct=True))
        .filter(id=tag_id)
        .first()
    )


def get_deck_tags_by_ids(tag_ids: list[str]) -> list[DeckTag]:
    return list(DeckTag.objects.filter(id__in=tag_ids).order_by("kind", "label", "id"))


def get_type_tag_by_key(key: str) -> DeckTag | None:
    return DeckTag.objects.filter(kind="type", key=key).first()


def deck_tag_key_exists(*, kind: DeckTagKind, key: str, exclude_id: str | None = None) -> bool:
    query = DeckTag.objects.filter(kind=kind, key=key)
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    return query.exists()


def list_decks_for_tag(tag_id: str) -> list[Deck]:
    return list(
        deck_summary_queryset()
        .filter(tag_assignments__tag_id=tag_id)
        .distinct()
        .order_by("-updated_at", "-created_at", "id")
    )


def list_deck_tag_suggestions(*, status: str | None = None) -> list[DeckTagSuggestion]:
    query = DeckTagSuggestion.objects.select_related("accepted_tag").annotate(
        occurrence_count=Count("deck_occurrences__deck", distinct=True)
    )
    if status is not None:
        query = query.filter(status=status)
    return list(query.order_by("status", "display_value", "id"))


def get_deck_tag_suggestion(suggestion_id: str) -> DeckTagSuggestion | None:
    return (
        DeckTagSuggestion.objects.select_related("accepted_tag")
        .annotate(occurrence_count=Count("deck_occurrences__deck", distinct=True))
        .filter(id=suggestion_id)
        .first()
    )


def get_deck_tag_suggestion_by_value(normalized_value: str) -> DeckTagSuggestion | None:
    return DeckTagSuggestion.objects.select_related("accepted_tag").filter(
        kind="type",
        normalized_value=normalized_value,
    ).first()


def list_decks_for_suggestion(suggestion_id: str) -> list[Deck]:
    return list(
        deck_summary_queryset()
        .filter(tag_suggestion_occurrences__suggestion_id=suggestion_id)
        .distinct()
        .order_by("-updated_at", "-created_at", "id")
    )

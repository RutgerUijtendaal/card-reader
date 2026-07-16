from __future__ import annotations

from card_reader_core.models import (
    Deck,
    DeckTag,
    DeckTagAssignment,
    DeckTagKind,
    DeckTagSuggestion,
    DeckTagSuggestionDeck,
    now_utc,
)


def create_deck_tag(*, kind: DeckTagKind, key: str, label: str) -> DeckTag:
    return DeckTag.objects.create(kind=kind, key=key, label=label)


def update_deck_tag(*, tag: DeckTag, kind: DeckTagKind, key: str, label: str) -> DeckTag:
    tag.kind = kind
    tag.key = key
    tag.label = label
    tag.updated_at = now_utc()
    tag.save(update_fields=["kind", "key", "label", "updated_at"])
    return tag


def delete_deck_tag(*, tag_id: str) -> bool:
    deleted, _ = DeckTag.objects.filter(id=tag_id).delete()
    return deleted > 0


def replace_deck_tag_assignments(*, deck: Deck, tags: list[DeckTag]) -> None:
    DeckTagAssignment.objects.filter(deck=deck).delete()
    DeckTagAssignment.objects.bulk_create(
        [DeckTagAssignment(deck=deck, tag=tag) for tag in tags],
        ignore_conflicts=True,
    )


def clear_pending_suggestion_occurrences(*, deck: Deck) -> None:
    DeckTagSuggestionDeck.objects.filter(deck=deck, suggestion__status="pending").delete()


def attach_pending_suggestion(*, deck: Deck, suggestion: DeckTagSuggestion) -> None:
    DeckTagSuggestionDeck.objects.get_or_create(deck=deck, suggestion=suggestion)


def get_or_create_deck_tag_suggestion(*, normalized_value: str, display_value: str) -> DeckTagSuggestion:
    suggestion, _created = DeckTagSuggestion.objects.get_or_create(
        kind="type",
        normalized_value=normalized_value,
        defaults={"display_value": display_value},
    )
    return suggestion


def accept_deck_tag_suggestion(*, suggestion: DeckTagSuggestion, tag: DeckTag) -> DeckTagSuggestion:
    suggestion.status = "accepted"
    suggestion.accepted_tag = tag
    suggestion.updated_at = now_utc()
    suggestion.save(update_fields=["status", "accepted_tag", "updated_at"])
    DeckTagAssignment.objects.bulk_create(
        [
            DeckTagAssignment(deck_id=deck_id, tag=tag)
            for deck_id in suggestion.deck_occurrences.values_list("deck_id", flat=True)
        ],
        ignore_conflicts=True,
    )
    return suggestion


def reject_deck_tag_suggestion(*, suggestion: DeckTagSuggestion) -> DeckTagSuggestion:
    suggestion.status = "rejected"
    suggestion.accepted_tag = None
    suggestion.updated_at = now_utc()
    suggestion.save(update_fields=["status", "accepted_tag", "updated_at"])
    return suggestion

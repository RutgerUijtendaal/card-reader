from __future__ import annotations

from django.db.models import F

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


def reject_accepted_deck_tag_suggestions(*, tag_id: str) -> int:
    return DeckTagSuggestion.objects.filter(
        accepted_tag_id=tag_id,
        status="accepted",
    ).update(
        status="rejected",
        accepted_tag=None,
        updated_at=now_utc(),
    )


def replace_deck_tag_assignments(*, deck: Deck, tags: list[DeckTag]) -> None:
    DeckTagAssignment.objects.filter(deck=deck).delete()
    DeckTagAssignment.objects.bulk_create(
        [DeckTagAssignment(deck=deck, tag=tag) for tag in tags],
        ignore_conflicts=True,
    )


def deactivate_unresolved_suggestion_occurrences(*, deck: Deck) -> None:
    DeckTagSuggestionDeck.objects.filter(
        deck=deck,
        suggestion__status__in=["pending", "rejected"],
        is_active=True,
    ).update(is_active=False, updated_at=now_utc())


def attach_suggestion_occurrence(*, deck: Deck, suggestion: DeckTagSuggestion) -> None:
    DeckTagSuggestionDeck.objects.update_or_create(
        deck=deck,
        suggestion=suggestion,
        defaults={"is_active": True, "updated_at": now_utc()},
    )


def record_rejected_suggestion_resubmission(*, suggestion: DeckTagSuggestion) -> DeckTagSuggestion:
    DeckTagSuggestion.objects.filter(id=suggestion.id).update(
        rejected_resubmission_count=F("rejected_resubmission_count") + 1,
        updated_at=now_utc(),
    )
    suggestion.refresh_from_db(fields=["rejected_resubmission_count", "updated_at"])
    return suggestion


def get_or_create_deck_tag_suggestion(*, normalized_value: str, display_value: str) -> DeckTagSuggestion:
    suggestion, _created = DeckTagSuggestion.objects.get_or_create(
        kind="type",
        normalized_value=normalized_value,
        defaults={"display_value": display_value},
    )
    return suggestion


def accept_deck_tag_suggestion(*, suggestion: DeckTagSuggestion, tag: DeckTag) -> DeckTagSuggestion:
    active_occurrences = suggestion.deck_occurrences.filter(is_active=True)
    active_deck_ids = list(active_occurrences.values_list("deck_id", flat=True))
    suggestion.status = "accepted"
    suggestion.accepted_tag = tag
    suggestion.updated_at = now_utc()
    suggestion.save(update_fields=["status", "accepted_tag", "updated_at"])
    DeckTagAssignment.objects.bulk_create(
        [DeckTagAssignment(deck_id=deck_id, tag=tag) for deck_id in active_deck_ids],
        ignore_conflicts=True,
    )
    active_occurrences.update(is_active=False, updated_at=now_utc())
    return suggestion


def reject_deck_tag_suggestion(*, suggestion: DeckTagSuggestion) -> DeckTagSuggestion:
    suggestion.status = "rejected"
    suggestion.accepted_tag = None
    suggestion.updated_at = now_utc()
    suggestion.save(update_fields=["status", "accepted_tag", "updated_at"])
    suggestion.deck_occurrences.filter(is_active=True).update(is_active=False, updated_at=now_utc())
    return suggestion


def reopen_deck_tag_suggestion(*, suggestion: DeckTagSuggestion) -> DeckTagSuggestion:
    suggestion.status = "pending"
    suggestion.accepted_tag = None
    suggestion.updated_at = now_utc()
    suggestion.save(update_fields=["status", "accepted_tag", "updated_at"])
    return suggestion

from __future__ import annotations

from rest_framework import serializers

from card_reader_api.decks.serializers import deck_hero_summary_payload
from card_reader_core.models import Deck, DeckTag, DeckTagSuggestion
from card_reader_core.services.deck_tags import DeckTagDetail, DeckTagSuggestionDetail


def deck_tag_payload(tag: DeckTag) -> dict[str, object]:
    return {
        "id": tag.id,
        "kind": tag.kind,
        "key": tag.key,
        "label": tag.label,
        "linked_deck_count": int(getattr(tag, "linked_deck_count", 0)),
    }


def linked_deck_payload(deck: Deck) -> dict[str, object]:
    return {
        "id": deck.id,
        "name": deck.name,
        "visibility": deck.visibility,
        "owner": {
            "id": str(getattr(deck.owner, "pk", "")),
            "username": deck.owner.get_username(),
        },
        "hero_card": deck_hero_summary_payload(deck.hero_card, allow_game_master_cards=True),
        "updated_at": deck.updated_at.isoformat(),
    }


def deck_tag_detail_payload(detail: DeckTagDetail) -> dict[str, object]:
    payload = deck_tag_payload(detail["entry"])
    payload["linked_deck_count"] = detail["linked_deck_count"]
    payload["linked_decks"] = [linked_deck_payload(deck) for deck in detail["linked_decks"]]
    return payload


def deck_tag_suggestion_payload(suggestion: DeckTagSuggestion) -> dict[str, object]:
    accepted_target = deck_tag_payload(suggestion.accepted_tag) if suggestion.accepted_tag is not None else None
    return {
        "id": suggestion.id,
        "kind": suggestion.kind,
        "display_value": suggestion.display_value,
        "normalized_value": suggestion.normalized_value,
        "status": suggestion.status,
        "occurrence_count": int(getattr(suggestion, "occurrence_count", 0)),
        "active_occurrence_count": int(getattr(suggestion, "active_occurrence_count", 0)),
        "rejected_resubmission_count": suggestion.rejected_resubmission_count,
        "accepted_target": accepted_target,
    }


def deck_tag_suggestion_detail_payload(detail: DeckTagSuggestionDetail) -> dict[str, object]:
    payload = deck_tag_suggestion_payload(detail["entry"])
    payload["occurrence_count"] = detail["occurrence_count"]
    payload["active_occurrence_count"] = detail["active_occurrence_count"]
    payload["linked_decks"] = [linked_deck_payload(deck) for deck in detail["linked_decks"]]
    return payload


class DeckTagWriteSerializer(serializers.Serializer[dict[str, object]]):
    kind = serializers.ChoiceField(choices=["role", "type"], required=True)
    label = serializers.CharField(required=True, allow_blank=False)  # type: ignore[assignment]
    key = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class DeckTagSuggestionAcceptSerializer(serializers.Serializer[dict[str, object]]):
    target_id = serializers.CharField(required=False, allow_blank=False)
    label = serializers.CharField(required=False, allow_blank=False, allow_null=True)  # type: ignore[assignment]
    key = serializers.CharField(required=False, allow_blank=True, allow_null=True)

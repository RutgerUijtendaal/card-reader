from __future__ import annotations

from typing import Any
from rest_framework import serializers

from card_reader_api.decks.serializers import deck_card_payload
from card_reader_core.models import CARD_FACTIONS
from card_reader_core.models.encounter import Encounter
from card_reader_core.services.card_backs import ResolvedCardBack, resolve_effective_card_backs
from card_reader_core.services.encounters import boss_cards, validation_issues


class EntrySerializer(serializers.Serializer[dict[str, Any]]):
    card_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class EncounterWriteSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(allow_blank=True, required=False)
    description_markup = serializers.CharField(allow_blank=True, required=False)
    long_description_markup = serializers.CharField(allow_blank=True, required=False)
    boss_card_id = serializers.CharField(allow_null=True, required=False)
    boss_group_id = serializers.CharField(allow_null=True, required=False)
    visibility = serializers.ChoiceField(choices=["private", "public"], required=False)
    factions = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_FACTIONS), required=False
    )
    entries = EntrySerializer(many=True, required=False)
    revision = serializers.IntegerField(min_value=1, required=False)


class EncounterListSerializer(serializers.Serializer[dict[str, Any]]):
    q = serializers.CharField(default="", allow_blank=True)
    factions = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_FACTIONS), default=list
    )
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=24, min_value=1, max_value=100)


def encounter_summaries(records: list[Encounter]) -> list[dict[str, object]]:
    backs = resolve_effective_card_backs(
        [record.boss_card_id for record in records if record.boss_card_id]
    )
    return [encounter_payload(record, detail=False, resolved_backs=backs) for record in records]


def encounter_payload(
    record: Encounter,
    *,
    detail: bool = True,
    resolved_backs: dict[str, ResolvedCardBack] | None = None,
) -> dict[str, object]:
    entries = list(record.entries.all()) if detail else []
    bosses = boss_cards(record) if detail else []
    cards = [*bosses, *[entry.card for entry in entries]]
    if record.boss_card:
        cards.append(record.boss_card)
    backs = (
        resolve_effective_card_backs([card.id for card in cards])
        if resolved_backs is None
        else resolved_backs
    )
    payloads = {
        card.id: deck_card_payload(card, resolved_card_back=backs.get(card.id)) for card in cards
    }
    issues = validation_issues(record)
    result: dict[str, object] = {
        "id": record.id,
        "name": record.name,
        "description": record.description,
        "factions": record.factions,
        "visibility": record.visibility,
        "revision": record.revision,
        "creator": {"id": str(record.creator_id), "username": record.creator.get_username()},
        "boss_card_id": record.boss_card_id,
        "boss_group_id": record.boss_group_id,
        "boss_card": payloads.get(record.boss_card_id or ""),
        "total_cards": getattr(record, "total_cards", sum(entry.quantity for entry in entries)),
        "status": {"is_valid": not issues, "issues": issues},
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
    if detail:
        result.update(
            {
                "description_markup": record.description_markup,
                "long_description": record.long_description,
                "long_description_markup": record.long_description_markup,
                "boss_cards": [payloads[card.id] for card in bosses],
                "entries": [
                    {
                        "card_id": entry.card_id,
                        "card": payloads[entry.card_id],
                        "quantity": entry.quantity,
                    }
                    for entry in entries
                ],
            }
        )
    return result

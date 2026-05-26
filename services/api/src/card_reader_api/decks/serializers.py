from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict, cast

from rest_framework import serializers
from rest_framework.response import Response

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import card_payload
from card_reader_core.models import Card, CardVersion, Deck
from card_reader_core.repositories.cards_repository import get_card_image
from card_reader_core.services.cards import CardMetadata
from card_reader_core.services.decks import DeckService


class DeckListFilterParams(TypedDict):
    hero_query: str | None
    card_query: str | None
    affinity_symbol_ids: list[str] | None
    affinity_symbol_match: str | None


def deck_payload(deck: Deck) -> dict[str, object]:
    validation = DeckService().get_deck_validation(deck)
    totals = DeckService().get_deck_totals(deck)
    entries = list(deck.entries.all())
    sideboards = list(deck.sideboards.all())
    return {
        "id": deck.id,
        "name": deck.name,
        "description": deck.description,
        "is_public": deck.is_public,
        "owner": {
            "id": str(getattr(deck.owner, "pk", "")),
            "username": deck.owner.get_username(),
        },
        "hero_card": deck_card_payload(deck.hero_card),
        "mainboard": {
            "total_cards": totals.mainboard_total_cards,
            "unique_cards": totals.mainboard_unique_cards,
            "entries": [
                {
                    "quantity": entry.quantity,
                    "card": deck_card_payload(entry.card),
                }
                for entry in entries
            ],
        },
        "sideboards": [
            {
                "id": sideboard.id,
                "name": sideboard.name,
                "total_cards": sum(int(entry.quantity) for entry in sideboard.entries.all()),
                "unique_cards": sideboard.entries.count(),
                "entries": [
                    {
                        "quantity": entry.quantity,
                        "card": deck_card_payload(entry.card),
                    }
                    for entry in sideboard.entries.all()
                ],
            }
            for sideboard in sideboards
        ],
        "totals": {
            "overall_total_cards": totals.overall_total_cards,
            "overall_unique_cards": totals.overall_unique_cards,
            "mainboard_total_cards": totals.mainboard_total_cards,
            "mainboard_unique_cards": totals.mainboard_unique_cards,
        },
        "status": {
            "is_valid": validation.is_valid,
            "label": validation.status_label,
            "issues": validation.issues,
        },
        "created_at": deck.created_at.isoformat(),
        "updated_at": deck.updated_at.isoformat(),
    }


def deck_card_payload(card: Card) -> dict[str, object]:
    version = card.latest_version
    if version is None:
        return {
            "id": card.id,
            "result_type": "card",
            "key": card.key,
            "label": card.label,
            "is_hero": card.is_hero,
            "template_id": "",
            "version_id": "",
            "version_number": 0,
            "previous_version_id": None,
            "is_latest": True,
            "name": card.label,
            "type_line": "",
            "mana_cost": "",
            "mana_symbols": [],
            "attack": None,
            "health": None,
            "rules_text": "",
            "confidence": 0.0,
            "created_at": "",
            "image_url": None,
            "keywords": [],
            "tags": [],
            "symbols": [],
            "types": [],
        }

    image = get_card_image(version.id)
    metadata = _deck_card_metadata(version)
    return card_payload(
        card,
        version,
        image_url=card_image_asset_url(image, fallback_url=f"/cards/{card.id}/image"),
        metadata=metadata,
    )


def _deck_card_metadata(version: CardVersion) -> CardMetadata:
    return {
        "keywords": [
            row.keyword
            for row in sorted(version.card_version_keywords.all(), key=lambda row: row.keyword.label)
        ],
        "tags": [
            row.tag
            for row in sorted(version.card_version_tags.all(), key=lambda row: row.tag.label)
        ],
        "symbols": [
            row.symbol
            for row in sorted(version.card_version_symbols.all(), key=lambda row: row.symbol.label)
        ],
        "types": [
            row.type
            for row in sorted(version.card_version_types.all(), key=lambda row: row.type.label)
        ],
    }


class MainboardEntryWriteSerializer(serializers.Serializer[dict[str, object]]):
    card_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1, max_value=4)


class SideboardEntryWriteSerializer(serializers.Serializer[dict[str, object]]):
    card_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class DeckSideboardWriteSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=True, allow_blank=False)
    entries = SideboardEntryWriteSerializer(many=True, required=True, allow_empty=True)


class DeckWriteSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=True, allow_blank=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_public = serializers.BooleanField(required=True)
    hero_card_id = serializers.CharField(required=True)
    entries = MainboardEntryWriteSerializer(many=True, required=True, allow_empty=True)
    sideboards = DeckSideboardWriteSerializer(many=True, required=False, allow_empty=True, default=list)


class DeckListQuerySerializer(serializers.Serializer[dict[str, object]]):
    hero_q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    affinity_symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    affinity_symbol_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)

    def validated_list_filters(self) -> DeckListFilterParams:
        return {
            "hero_query": self._string_or_none("hero_q"),
            "card_query": self._string_or_none("card_q"),
            "affinity_symbol_ids": self._string_list_or_none("affinity_symbol_ids"),
            "affinity_symbol_match": self._string_or_none("affinity_symbol_match"),
        }

    def _string_or_none(self, key: str) -> str | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, str) else None

    def _string_list_or_none(self, key: str) -> list[str] | None:
        value = self.validated_data.get(key)
        if not isinstance(value, list):
            return None
        out = [item for item in value if isinstance(item, str)]
        return out or None


def serializer_error(serializer: serializers.BaseSerializer[Any]) -> Response:
    errors = serializer.errors
    detail = next(iter(cast(Mapping[str, object], errors).values()), "Invalid request.")
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=400)

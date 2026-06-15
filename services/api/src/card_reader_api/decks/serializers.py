from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict, cast

from rest_framework import serializers

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import card_payload, symbol_option
from card_reader_core.models import Card, CardVersion, CardVersionImage, Deck, DeckVisibility
from card_reader_core.repositories.cards import get_card_image
from card_reader_core.services.cards import CardMetadata
from card_reader_core.services.decks import DeckConstraintEntry, DeckService, effective_deck_building_rules_json, normalize_deck_building_config


class DeckListFilterParams(TypedDict):
    search_query: str | None
    hero_query: str | None
    author_query: str | None
    card_query: str | None
    affinity_symbol_ids: list[str] | None
    affinity_symbol_exclude_ids: list[str] | None
    affinity_symbol_match: str | None


def deck_summary_payload(deck: Deck) -> dict[str, object]:
    validation = DeckService().get_deck_validation(deck)
    totals = DeckService().get_deck_totals(deck)
    return {
        "id": deck.id,
        "name": deck.name,
        "description": deck.description,
        "visibility": deck.visibility,
        "owner": {
            "id": str(getattr(deck.owner, "pk", "")),
            "username": deck.owner.get_username(),
        },
        "hero_card": deck_hero_summary_payload(deck.hero_card),
        "mainboard": {
            "total_cards": totals.mainboard_total_cards,
            "unique_cards": totals.mainboard_unique_cards,
        },
        "sideboard_count": len(list(deck.sideboards.all())),
        "status": {
            "is_valid": validation.is_valid,
            "label": validation.status_label,
            "deprecated_card_count": validation.deprecated_card_count,
        },
        "created_at": deck.created_at.isoformat(),
        "updated_at": deck.updated_at.isoformat(),
    }


def deck_payload(deck: Deck) -> dict[str, object]:
    validation = DeckService().get_deck_validation(deck)
    totals = DeckService().get_deck_totals(deck)
    entries = list(deck.entries.all())
    sideboards = list(deck.sideboards.all())
    constraint_entries = [
        DeckConstraintEntry(card=entry.card, quantity=int(entry.quantity), board="mainboard")
        for entry in entries
    ]
    constraint_entries.extend(
        DeckConstraintEntry(card=entry.card, quantity=int(entry.quantity), board="sideboard")
        for sideboard in sideboards
        for entry in sideboard.entries.all()
    )
    return {
        "id": deck.id,
        "name": deck.name,
        "description": deck.description,
        "visibility": deck.visibility,
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
            "warnings": validation.warnings,
            "deprecated_card_count": validation.deprecated_card_count,
            "deprecated_card_ids": validation.deprecated_card_ids or [],
        },
        "deck_building_rules": effective_deck_building_rules_json(
            hero_card=deck.hero_card,
            entries=constraint_entries,
        ),
        "created_at": deck.created_at.isoformat(),
        "updated_at": deck.updated_at.isoformat(),
    }


def deck_hero_summary_payload(card: Card) -> dict[str, object]:
    version = card.latest_version
    if version is None:
        return {
            "id": card.id,
            "key": card.key,
            "label": card.label,
            "name": card.label,
            "image_url": None,
            "symbols": [],
        }

    images = version.images.all()
    image_url = _prefetched_card_image_asset_url(images, fallback_url=f"/cards/{card.id}/image")
    return {
        "id": card.id,
        "key": card.key,
        "label": card.label,
        "name": version.name,
        "image_url": image_url,
        "symbols": [
            symbol_option(row.symbol)
            for row in version.card_version_symbols.all()
            if row.symbol.symbol_type == "affinity"
        ],
    }


def _prefetched_card_image_asset_url(
    images: Iterable[CardVersionImage],
    *,
    fallback_url: str,
) -> str | None:
    first_image: CardVersionImage | None = None
    for image in images:
        if first_image is None:
            first_image = image
        image_url = card_image_asset_url(image, fallback_url=fallback_url)
        if image_url is not None:
            return image_url
    return card_image_asset_url(first_image, fallback_url=fallback_url)


def deck_card_payload(card: Card) -> dict[str, object]:
    version = card.latest_version
    if version is None:
        return {
            "id": card.id,
            "result_type": "card",
            "key": card.key,
            "label": card.label,
            "is_hero": card.is_hero,
            "deck_building_config": normalize_deck_building_config(card.deck_building_config_json),
            "lifecycle_status": card.lifecycle_status,
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
    quantity = serializers.IntegerField(min_value=1)


class SideboardEntryWriteSerializer(serializers.Serializer[dict[str, object]]):
    card_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class DeckSideboardWriteSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=True, allow_blank=False)
    entries = SideboardEntryWriteSerializer(many=True, required=True, allow_empty=True)


class DeckWriteSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=True, allow_blank=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    visibility = serializers.ChoiceField(choices=cast(tuple[DeckVisibility, ...], ("private", "unlisted", "public")), required=True)
    hero_card_id = serializers.CharField(required=True)
    entries = MainboardEntryWriteSerializer(many=True, required=True, allow_empty=True)
    sideboards = DeckSideboardWriteSerializer(many=True, required=False, allow_empty=True, default=list)


class DeckListQuerySerializer(serializers.Serializer[dict[str, object]]):
    q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    view = serializers.ChoiceField(choices=['summary'], required=False, allow_null=True)
    hero_q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    author_q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    affinity_symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    affinity_symbol_exclude_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    affinity_symbol_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)

    def validated_list_filters(self) -> DeckListFilterParams:
        return {
            "search_query": self._string_or_none("q"),
            "hero_query": self._string_or_none("hero_q"),
            "author_query": self._string_or_none("author_q"),
            "card_query": self._string_or_none("card_q"),
            "affinity_symbol_ids": self._string_list_or_none("affinity_symbol_ids"),
            "affinity_symbol_exclude_ids": self._string_list_or_none("affinity_symbol_exclude_ids"),
            "affinity_symbol_match": self._string_or_none("affinity_symbol_match"),
        }

    def wants_summary(self) -> bool:
        return self._string_or_none("view") == "summary"

    def _string_or_none(self, key: str) -> str | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, str) else None

    def _string_list_or_none(self, key: str) -> list[str] | None:
        value = self.validated_data.get(key)
        if not isinstance(value, list):
            return None
        out = [item for item in value if isinstance(item, str)]
        return out or None

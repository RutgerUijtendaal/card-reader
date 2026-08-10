from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import TypedDict, cast

from rest_framework import serializers

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import card_payload, symbol_option
from card_reader_core.metadata import NO_MANA_FAMILY_SORT_KEY
from card_reader_core.models import (
    Card,
    CardPoolScope,
    CardVersion,
    CardVersionImage,
    Deck,
    DeckDifficulty,
    DeckEntry,
    DeckSideboard,
    DeckVisibility,
    card_role_keys,
)
from card_reader_core.repositories.cards import get_card_image
from card_reader_core.services.cards import CardMetadata
from card_reader_core.services.decks import DeckConstraintEntry, DeckService, effective_deck_building_rules_json, normalize_deck_building_config
from card_reader_core.services.deck_tags import DeckTagSuggestionResolution


class DeckListFilterParams(TypedDict):
    search_query: str | None
    hero_query: str | None
    author_query: str | None
    card_query: str | None
    affinity_symbol_ids: list[str] | None
    affinity_symbol_exclude_ids: list[str] | None
    affinity_symbol_match: str | None
    deck_tag_ids: list[str] | None
    deck_tag_exclude_ids: list[str] | None
    deck_tag_match: str | None


def deck_summary_payload(
    deck: Deck,
    *,
    card_pool_scope: CardPoolScope,
    include_pending_suggestions: bool = False,
) -> dict[str, object]:
    entries = list(deck.entries.all())
    sideboards = list(deck.sideboards.all())
    has_restricted_cards = _deck_contains_restricted_cards(
        deck,
        card_pool_scope=card_pool_scope,
        entries=entries,
        sideboards=sideboards,
    )
    validation = None if has_restricted_cards else DeckService().get_deck_validation(deck)
    totals = DeckService().get_deck_totals(deck)
    return {
        "id": deck.id,
        "name": deck.name,
        "description": deck.description,
        "difficulty": deck.difficulty,
        "visibility": deck.visibility,
        "owner": {
            "id": str(getattr(deck.owner, "pk", "")),
            "username": deck.owner.get_username(),
        },
        "hero_card": deck_hero_summary_payload(
            deck.hero_card,
            card_pool_scope=card_pool_scope,
        ),
        "mainboard": {
            "total_cards": totals.mainboard_total_cards,
            "unique_cards": totals.mainboard_unique_cards,
        },
        "sideboard_count": len(sideboards),
        "status": {
            "is_valid": False if validation is None else validation.is_valid,
            "label": "In Progress" if validation is None else validation.status_label,
            "deprecated_card_count": 0 if validation is None else validation.deprecated_card_count,
        },
        "tags": deck_tags_payload(deck),
        "pending_tag_suggestions": pending_deck_tag_suggestions_payload(deck)
        if include_pending_suggestions
        else [],
        "created_at": deck.created_at.isoformat(),
        "updated_at": deck.updated_at.isoformat(),
    }


def deck_payload(
    deck: Deck,
    *,
    card_pool_scope: CardPoolScope,
    include_pending_suggestions: bool = False,
) -> dict[str, object]:
    totals = DeckService().get_deck_totals(deck)
    entries = list(deck.entries.all())
    sideboards = list(deck.sideboards.all())
    has_restricted_cards = _deck_contains_restricted_cards(
        deck,
        card_pool_scope=card_pool_scope,
        entries=entries,
        sideboards=sideboards,
    )
    validation = None if has_restricted_cards else DeckService().get_deck_validation(deck)
    constraint_entries = [
        DeckConstraintEntry(card=entry.card, quantity=int(entry.quantity), board="mainboard")
        for entry in entries
        if card_pool_scope.allows_card_pool(entry.card.card_pool)
    ]
    constraint_entries.extend(
        DeckConstraintEntry(card=entry.card, quantity=int(entry.quantity), board="sideboard")
        for sideboard in sideboards
        for entry in sideboard.entries.all()
        if card_pool_scope.allows_card_pool(entry.card.card_pool)
    )
    return {
        "id": deck.id,
        "name": deck.name,
        "description": deck.description,
        "long_description": deck.long_description,
        "difficulty": deck.difficulty,
        "visibility": deck.visibility,
        "owner": {
            "id": str(getattr(deck.owner, "pk", "")),
            "username": deck.owner.get_username(),
        },
        "hero_card": deck_card_payload(
            deck.hero_card,
            card_pool_scope=card_pool_scope,
        ),
        "mainboard": {
            "total_cards": totals.mainboard_total_cards,
            "unique_cards": totals.mainboard_unique_cards,
            "entries": [
                {
                    "quantity": entry.quantity,
                    "card": deck_card_payload(
                        entry.card,
                        card_pool_scope=card_pool_scope,
                    ),
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
                        "card": deck_card_payload(
                            entry.card,
                            card_pool_scope=card_pool_scope,
                        ),
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
            "is_valid": False if validation is None else validation.is_valid,
            "label": "In Progress" if validation is None else validation.status_label,
            "issues": (
                ["Deck contains cards that are unavailable in the Player workspace."]
                if validation is None
                else validation.issues
            ),
            "warnings": [] if validation is None else validation.warnings,
            "deprecated_card_count": 0 if validation is None else validation.deprecated_card_count,
            "deprecated_card_ids": [] if validation is None else validation.deprecated_card_ids or [],
        },
        "deck_building_rules": effective_deck_building_rules_json(
            hero_card=(
                deck.hero_card
                if card_pool_scope.allows_card_pool(deck.hero_card.card_pool)
                else None
            ),
            entries=constraint_entries,
        ),
        "tags": deck_tags_payload(deck),
        "pending_tag_suggestions": pending_deck_tag_suggestions_payload(deck)
        if include_pending_suggestions
        else [],
        "created_at": deck.created_at.isoformat(),
        "updated_at": deck.updated_at.isoformat(),
    }


def _deck_contains_restricted_cards(
    deck: Deck,
    *,
    card_pool_scope: CardPoolScope,
    entries: Iterable[DeckEntry],
    sideboards: Iterable[DeckSideboard],
) -> bool:
    if not card_pool_scope.allows_card_pool(deck.hero_card.card_pool):
        return True
    if any(not card_pool_scope.allows_card_pool(entry.card.card_pool) for entry in entries):
        return True
    return any(
        not card_pool_scope.allows_card_pool(entry.card.card_pool)
        for sideboard in sideboards
        for entry in sideboard.entries.all()
    )


def deck_tags_payload(deck: Deck) -> list[dict[str, object]]:
    return [
        {
            "id": assignment.tag.id,
            "key": assignment.tag.key,
            "label": assignment.tag.label,
            "kind": assignment.tag.kind,
        }
        for assignment in deck.tag_assignments.all()
    ]


def pending_deck_tag_suggestions_payload(deck: Deck) -> list[dict[str, object]]:
    return [
        {
            "id": occurrence.suggestion.id,
            "label": occurrence.suggestion.display_value,
            "normalized_value": occurrence.suggestion.normalized_value,
            "kind": occurrence.suggestion.kind,
            "status": occurrence.suggestion.status,
        }
        for occurrence in deck.tag_suggestion_occurrences.all()
        if occurrence.suggestion.status == "pending"
    ]


def deck_tag_suggestion_results_payload(
    results: list[DeckTagSuggestionResolution],
) -> list[dict[str, object]]:
    return [
        {
            "label": result["label"],
            "normalized_value": result["normalized_value"],
            "status": result["status"],
            "message": result["message"],
            "suggestion_id": result["suggestion_id"],
            "tag": (
                {
                    "id": result["tag"].id,
                    "key": result["tag"].key,
                    "label": result["tag"].label,
                    "kind": result["tag"].kind,
                }
                if result["tag"] is not None
                else None
            ),
        }
        for result in results
    ]


def deck_hero_summary_payload(
    card: Card,
    *,
    card_pool_scope: CardPoolScope,
) -> dict[str, object]:
    if not card_pool_scope.allows_card_pool(card.card_pool):
        return _restricted_deck_card_summary(card)
    version = card.latest_version
    if version is None:
        return {
            "id": card.id,
            "key": card.key,
            "label": card.label,
            "card_pool": card.card_pool,
            "card_roles": list(card_role_keys(card)),
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
        "card_pool": card.card_pool,
        "card_roles": list(card_role_keys(card)),
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


def deck_card_payload(
    card: Card,
    *,
    card_pool_scope: CardPoolScope,
) -> dict[str, object]:
    if not card_pool_scope.allows_card_pool(card.card_pool):
        return _restricted_deck_card_payload(card)
    version = card.latest_version
    if version is None:
        return {
            "id": card.id,
            "result_type": "card",
            "key": card.key,
            "label": card.label,
            "card_pool": card.card_pool,
            "card_roles": list(card_role_keys(card)),
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
            "mana_value": None,
            "mana_family_sort_key": NO_MANA_FAMILY_SORT_KEY,
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


def _restricted_deck_card_summary(card: Card) -> dict[str, object]:
    return {
        "id": card.id,
        "key": "restricted-game-master-card",
        "label": "Restricted Game Master card",
        "card_pool": card.card_pool,
        "card_roles": [],
        "name": "Restricted Game Master card",
        "image_url": None,
        "symbols": [],
        "restricted": True,
    }


def _restricted_deck_card_payload(card: Card) -> dict[str, object]:
    return {
        "id": card.id,
        "result_type": "card",
        "key": "restricted-game-master-card",
        "label": "Restricted Game Master card",
        "card_pool": card.card_pool,
        "card_roles": [],
        "deck_building_config": normalize_deck_building_config({}),
        "lifecycle_status": "active",
        "template_id": "",
        "version_id": "",
        "version_number": 0,
        "previous_version_id": None,
        "is_latest": True,
        "name": "Restricted Game Master card",
        "type_line": "",
        "mana_cost": "",
        "mana_symbols": [],
        "mana_value": None,
        "mana_family_sort_key": NO_MANA_FAMILY_SORT_KEY,
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
        "restricted": True,
    }


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
    long_description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    difficulty = serializers.ChoiceField(
        choices=cast(tuple[DeckDifficulty, ...], ("easy", "medium", "hard")),
        required=False,
        allow_null=True,
    )
    visibility = serializers.ChoiceField(choices=cast(tuple[DeckVisibility, ...], ("private", "unlisted", "public")), required=True)
    hero_card_id = serializers.CharField(required=True)
    entries = MainboardEntryWriteSerializer(many=True, required=True, allow_empty=True)
    sideboards = DeckSideboardWriteSerializer(many=True, required=False, allow_empty=True, default=list)
    tag_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True, default=list)
    suggested_type_labels = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        allow_empty=True,
        default=list,
    )


class DeckListQuerySerializer(serializers.Serializer[dict[str, object]]):
    q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    view = serializers.ChoiceField(choices=['summary'], required=False, allow_null=True)
    page = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    page_size = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=100)
    snapshot_at = serializers.DateTimeField(required=False, allow_null=True)
    cursor_created_at = serializers.DateTimeField(required=False, allow_null=True)
    cursor_id = serializers.CharField(required=False, allow_null=True)
    hero_q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    author_q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    affinity_symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    affinity_symbol_exclude_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    affinity_symbol_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)
    deck_tag_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    deck_tag_exclude_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    deck_tag_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        pagination_requested = any(
            attrs.get(key) is not None
            for key in ("page", "page_size", "snapshot_at", "cursor_created_at", "cursor_id")
        )
        if pagination_requested and attrs.get("view") != "summary":
            raise serializers.ValidationError({"view": "Pagination is only available for summary deck lists."})
        has_cursor_created_at = attrs.get("cursor_created_at") is not None
        has_cursor_id = attrs.get("cursor_id") is not None
        if has_cursor_created_at != has_cursor_id:
            raise serializers.ValidationError(
                {"cursor": "cursor_created_at and cursor_id must be provided together."}
            )
        return attrs

    def validated_list_filters(self) -> DeckListFilterParams:
        return {
            "search_query": self._string_or_none("q"),
            "hero_query": self._string_or_none("hero_q"),
            "author_query": self._string_or_none("author_q"),
            "card_query": self._string_or_none("card_q"),
            "affinity_symbol_ids": self._string_list_or_none("affinity_symbol_ids"),
            "affinity_symbol_exclude_ids": self._string_list_or_none("affinity_symbol_exclude_ids"),
            "affinity_symbol_match": self._string_or_none("affinity_symbol_match"),
            "deck_tag_ids": self._string_list_or_none("deck_tag_ids"),
            "deck_tag_exclude_ids": self._string_list_or_none("deck_tag_exclude_ids"),
            "deck_tag_match": self._string_or_none("deck_tag_match"),
        }

    def wants_summary(self) -> bool:
        return self._string_or_none("view") == "summary"

    def wants_pagination(self) -> bool:
        return any(
            self.validated_data.get(key) is not None
            for key in ("page", "page_size", "snapshot_at", "cursor_created_at", "cursor_id")
        )

    def pagination(self) -> tuple[int, int]:
        page = self.validated_data.get("page")
        page_size = self.validated_data.get("page_size")
        return (
            page if isinstance(page, int) else 1,
            page_size if isinstance(page_size, int) else 10,
        )

    def pagination_snapshot(self) -> datetime | None:
        value = self.validated_data.get("snapshot_at")
        return value if isinstance(value, datetime) else None

    def pagination_cursor(self) -> tuple[datetime | None, str | None]:
        created_at = self.validated_data.get("cursor_created_at")
        deck_id = self.validated_data.get("cursor_id")
        return (
            created_at if isinstance(created_at, datetime) else None,
            deck_id if isinstance(deck_id, str) else None,
        )

    def _string_or_none(self, key: str) -> str | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, str) else None

    def _string_list_or_none(self, key: str) -> list[str] | None:
        value = self.validated_data.get(key)
        if not isinstance(value, list):
            return None
        out = [item for item in value if isinstance(item, str)]
        return out or None

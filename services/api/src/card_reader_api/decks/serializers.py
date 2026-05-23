from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from rest_framework import serializers
from rest_framework.response import Response

from card_reader_core.models import Card, Deck
from card_reader_core.repositories.cards_repository import get_card_image
from card_reader_core.services.cards import resolve_card_image_path


def deck_payload(deck: Deck) -> dict[str, object]:
    entries = list(cast(Any, deck).entries.all())
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
            "total_cards": sum(entry.quantity for entry in entries),
            "unique_cards": len(entries),
            "entries": [
                {
                    "quantity": entry.quantity,
                    "card": deck_card_payload(entry.card),
                }
                for entry in entries
            ],
        },
        "created_at": deck.created_at.isoformat(),
        "updated_at": deck.updated_at.isoformat(),
    }


def deck_card_payload(card: Card) -> dict[str, object]:
    version = card.latest_version
    image = None if version is None else get_card_image(version.id)
    return {
        "id": card.id,
        "key": card.key,
        "label": card.label,
        "name": version.name if version is not None else card.label,
        "is_hero": card.is_hero,
        "image_url": f"/cards/{card.id}/image" if image and resolve_card_image_path(image) else None,
    }


class DeckEntryWriteSerializer(serializers.Serializer[dict[str, object]]):
    card_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1, max_value=4)


class DeckWriteSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=True, allow_blank=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_public = serializers.BooleanField(required=True)
    hero_card_id = serializers.CharField(required=True)
    entries = DeckEntryWriteSerializer(many=True, required=True, allow_empty=False)


def serializer_error(serializer: serializers.BaseSerializer[Any]) -> Response:
    errors = serializer.errors
    detail = next(iter(cast(Mapping[str, object], errors).values()), "Invalid request.")
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=400)

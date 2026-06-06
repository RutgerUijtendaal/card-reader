from __future__ import annotations

from rest_framework import serializers

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_core.models import CardVersion, CardVersionParseFlag, CardVersionParseFlagItem
from card_reader_core.repositories.cards import get_card_image


class ParseFlagItemsQuerySerializer(serializers.Serializer[dict[str, object]]):
    status = serializers.ChoiceField(choices=["open", "resolved", "dismissed", "all"], required=False, default="open")
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, default=50)


class ParseFlagItemUpdateSerializer(serializers.Serializer[dict[str, object]]):
    status = serializers.ChoiceField(choices=["resolved", "dismissed"])
    review_note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


def parse_flag_payload(flag: CardVersionParseFlag) -> dict[str, object]:
    version = flag.card_version
    card = version.card
    image = get_card_image(version.id)
    image_url = card_image_asset_url(image, fallback_url=f"/cards/{card.id}/versions/{version.id}/image")
    submitted_by = flag.submitted_by
    return {
        "id": flag.id,
        "note": flag.note,
        "created_at": flag.created_at.isoformat(),
        "updated_at": flag.updated_at.isoformat(),
        "submitted_by": {
            "id": str(submitted_by.pk),
            "username": submitted_by.get_username(),
        },
        "card": _card_payload(card_id=card.id, card_label=card.label, card_name=version.name, image_url=image_url),
        "version": _version_payload(version),
        "items": [_parse_flag_item_fields(item) for item in flag.items.all()],
    }


def parse_flag_item_payload(item: CardVersionParseFlagItem) -> dict[str, object]:
    flag = item.flag
    version = flag.card_version
    card = version.card
    image = get_card_image(version.id)
    image_url = card_image_asset_url(image, fallback_url=f"/cards/{card.id}/versions/{version.id}/image")
    submitted_by = flag.submitted_by
    return {
        **_parse_flag_item_fields(item),
        "flag_note": flag.note,
        "submitted_by": {
            "id": str(submitted_by.pk),
            "username": submitted_by.get_username(),
        },
        "card": _card_payload(card_id=card.id, card_label=card.label, card_name=version.name, image_url=image_url),
        "version": _version_payload(version),
    }


def _parse_flag_item_fields(item: CardVersionParseFlagItem) -> dict[str, object]:
    reviewed_by = item.reviewed_by
    return {
        "id": item.id,
        "flag_id": item.flag.id,
        "status": item.status,
        "property_key": item.property_key,
        "captured_current_value": item.captured_current_value,
        "expected_value": item.expected_value,
        "note": item.note,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "review_note": item.review_note,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "reviewed_by": None
        if reviewed_by is None
        else {
            "id": str(reviewed_by.pk),
            "username": reviewed_by.get_username(),
        },
    }


def _card_payload(*, card_id: str, card_label: str, card_name: str, image_url: str | None) -> dict[str, object]:
    return {
        "id": card_id,
        "label": card_label,
        "name": card_name,
        "image_url": image_url,
    }


def _version_payload(version: CardVersion) -> dict[str, object]:
    content_version = version.content_version
    return {
        "id": version.id,
        "version_number": version.version_number,
        "is_latest": version.is_latest,
        "content_version": None
        if content_version is None
        else {
            "id": content_version.id,
            "version_number": content_version.version_number,
        },
    }

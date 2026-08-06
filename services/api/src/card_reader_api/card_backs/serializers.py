from __future__ import annotations

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from card_reader_core.models import CardBack
from card_reader_core.services.card_backs import resolve_card_back_image_asset_path


def card_back_payload(card_back: CardBack) -> dict[str, object]:
    return {
        "id": card_back.id,
        "label": card_back.label,
        "original_filename": card_back.original_filename,
        "source_file": card_back.source_file,
        "stored_path": card_back.stored_path,
        "width": card_back.width,
        "height": card_back.height,
        "checksum": card_back.checksum,
        "is_current": card_back.is_current,
        "image_url": card_back_image_url(card_back),
        "created_at": card_back.created_at.isoformat(),
        "updated_at": card_back.updated_at.isoformat(),
    }


def public_card_back_payload(card_back: CardBack) -> dict[str, object]:
    return {
        "id": card_back.id,
        "label": card_back.label,
        "width": card_back.width,
        "height": card_back.height,
        "image_url": card_back_image_url(card_back),
        "created_at": card_back.created_at.isoformat(),
        "updated_at": card_back.updated_at.isoformat(),
    }


def current_card_back_payload(card_back: CardBack | None) -> dict[str, object]:
    return {"current": None if card_back is None else public_card_back_payload(card_back)}


def card_back_image_url(card_back: CardBack) -> str | None:
    asset_path = resolve_card_back_image_asset_path(card_back)
    return None if asset_path is None else f"/card-images/{asset_path}"


class CardBackUploadSerializer(serializers.Serializer[dict[str, object]]):
    file = serializers.FileField()
    label = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # type: ignore[assignment]

    def validate_file(self, value: UploadedFile) -> UploadedFile:
        if not value.name:
            raise serializers.ValidationError("file is required")
        return value

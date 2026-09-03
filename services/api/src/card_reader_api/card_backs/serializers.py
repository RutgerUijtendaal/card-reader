from __future__ import annotations

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from card_reader_core.models import CARD_FACTIONS, CARD_POOLS, CardBack
from card_reader_core.services.card_backs import ResolvedCardBack, resolve_card_back_image_asset_path


def card_back_payload(card_back: CardBack) -> dict[str, object]:
    pool_defaults = list(card_back.pool_defaults.all())
    default_pool_keys = {row.card_pool for row in pool_defaults}
    faction_defaults = list(card_back.faction_defaults.all())
    default_faction_keys = {row.faction for row in faction_defaults}
    return {
        "id": card_back.id,
        "label": card_back.label,
        "original_filename": card_back.original_filename,
        "source_file": card_back.source_file,
        "stored_path": card_back.stored_path,
        "width": card_back.width,
        "height": card_back.height,
        "checksum": card_back.checksum,
        "default_for_pools": [pool for pool in CARD_POOLS if pool in default_pool_keys],
        "default_for_factions": [
            faction for faction in CARD_FACTIONS if faction in default_faction_keys
        ],
        "override_card_count": int(getattr(card_back, "override_card_count", 0)),
        "is_usable": resolve_card_back_image_asset_path(card_back) is not None,
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


def resolved_card_back_payload(resolved: ResolvedCardBack | None) -> dict[str, object] | None:
    if resolved is None or resolved.source is None or resolved.card_back is None:
        return None
    payload: dict[str, object] = {
        "source": resolved.source,
        "asset": public_card_back_payload(resolved.card_back),
    }
    if resolved.faction is not None:
        payload["faction"] = resolved.faction
    return payload


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


class CardBackDefaultUpdateSerializer(serializers.Serializer[dict[str, object]]):
    card_back_id = serializers.CharField(allow_blank=False, allow_null=True)

from __future__ import annotations

import json

from models import Card, CardVersion
from schemas import (
    CardDetailResponse,
    CardGenerationResponse,
    CardSummaryResponse,
    MetadataOptionResponse,
)


def to_card_summary_response(card: Card, version: CardVersion) -> CardSummaryResponse:
    return CardSummaryResponse(
        id=card.id,
        key=card.key,
        label=card.label,
        name=version.name,
        template_id=version.template_id,
        version_id=version.id,
        version_number=version.version_number,
        is_latest=version.is_latest,
        type_line=version.type_line,
        mana_cost=version.mana_cost,
        attack=version.attack,
        health=version.health,
        confidence=version.confidence,
    )


def to_card_detail_response(
    card: Card,
    version: CardVersion,
    *,
    has_image: bool,
) -> CardDetailResponse:
    return CardDetailResponse(
        id=card.id,
        key=card.key,
        label=card.label,
        version_id=version.id,
        version_number=version.version_number,
        name=version.name,
        previous_version_id=version.previous_version_id,
        is_latest=version.is_latest,
        type_line=version.type_line,
        mana_cost=version.mana_cost,
        mana_symbols=_decode_mana_symbols(version.mana_symbols_json),
        attack=version.attack,
        health=version.health,
        rules_text=version.rules_text,
        confidence=version.confidence,
        image_url=f"/cards/{card.id}/image" if has_image else None,
    )


def to_card_generation_response(version: CardVersion) -> CardGenerationResponse:
    return CardGenerationResponse(
        id=version.id,
        version_number=version.version_number,
        name=version.name,
        type_line=version.type_line,
        mana_cost=version.mana_cost,
        mana_symbols=_decode_mana_symbols(version.mana_symbols_json),
        attack=version.attack,
        health=version.health,
        rules_text=version.rules_text,
        confidence=version.confidence,
        created_at=version.created_at.isoformat(),
    )


def to_metadata_option_response(meta: object) -> MetadataOptionResponse:
    return MetadataOptionResponse(
        id=str(getattr(meta, "id", "")),
        key=str(getattr(meta, "key", "")),
        label=str(getattr(meta, "label", "")),
    )


def _decode_mana_symbols(value: str) -> list[str]:
    try:
        payload = json.loads(value)
    except Exception:
        return []
    if isinstance(payload, list):
        return [str(item) for item in payload]
    return []

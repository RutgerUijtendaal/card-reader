from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass

from card_reader_core.services.exports import TtsCardExportData

TTS_CARD_EXPORT_SCHEMA = "card-reader.tts-cards.v2"


@dataclass(frozen=True)
class EncodedTtsCardExport:
    encoded_payload: str
    exported_count: int
    skipped_count: int
    sheet_count: int


def encode_tts_card_export(
    export: TtsCardExportData,
    *,
    absolute_url: Callable[[str], str],
) -> EncodedTtsCardExport:
    payload = build_tts_card_export_payload(export, absolute_url=absolute_url)
    encoded_payload = base64.b64encode(serialize_tts_card_export_payload(payload)).decode("ascii")
    return EncodedTtsCardExport(
        encoded_payload=encoded_payload,
        exported_count=sum(card.quantity for card in export.cards),
        skipped_count=sum(card.quantity for card in export.skipped),
        sheet_count=len(export.sheets),
    )


def build_tts_card_export_payload(
    export: TtsCardExportData,
    *,
    absolute_url: Callable[[str], str],
) -> dict[str, object]:
    collection: dict[str, object] = {
        "name": export.collection_name,
        "source": export.source_metadata,
    }
    if export.collection_description is not None:
        collection["description"] = export.collection_description

    return {
        "schema": TTS_CARD_EXPORT_SCHEMA,
        "collection": collection,
        "card_back_url": absolute_url(f"/card-images/{export.card_back_asset_path}"),
        "sheets": [
            {
                "sheet_id": sheet.sheet_id,
                "face_url": absolute_url(f"/tts/card-sheets/{sheet.sheet_id}/image.webp"),
                "columns": sheet.columns,
                "rows": sheet.rows,
                "revision": sheet.revision,
                "image_checksum": sheet.image_checksum,
            }
            for sheet in export.sheets
        ],
        "cards": [
            _optional_role(
                {
                    "card_id": card.card_id,
                    "card_version_id": card.card_version_id,
                    "name": card.name,
                    "quantity": card.quantity,
                    "sheet_id": card.sheet_id,
                    "slot_index": card.slot_index,
                    "image_checksum": card.image_checksum,
                    "lifecycle_status": card.lifecycle_status,
                },
                card.role,
            )
            for card in export.cards
        ],
        "skipped": [
            _optional_role(
                {
                    "card_id": card.card_id,
                    "name": card.name,
                    "quantity": card.quantity,
                    "reason": card.reason,
                },
                card.role,
            )
            for card in export.skipped
        ],
    }


def _optional_role(payload: dict[str, object], role: str | None) -> dict[str, object]:
    if role is not None:
        payload["role"] = role
    return payload


def serialize_tts_card_export_payload(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


__all__ = [
    "EncodedTtsCardExport",
    "TTS_CARD_EXPORT_SCHEMA",
    "build_tts_card_export_payload",
    "encode_tts_card_export",
    "serialize_tts_card_export_payload",
]

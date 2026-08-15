from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlencode

from card_reader_api.cards.tts_sheet_access import create_tts_sheet_access_token
from card_reader_core.models import PLAYER_CARD_POOL
from card_reader_core.services.exports import TtsCardExportData, TtsCardExportSheet

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
                "face_url": absolute_url(_sheet_face_path(sheet)),
                "card_pool": sheet.card_pool,
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


def _sheet_face_path(sheet: TtsCardExportSheet) -> str:
    sheet_id = sheet.sheet_id
    path = f"/tts/card-sheets/{sheet_id}/image.webp"
    if sheet.card_pool == PLAYER_CARD_POOL:
        return path
    token = create_tts_sheet_access_token(
        sheet_id=sheet_id,
        rendered_revision=sheet.revision,
        rendered_checksum=sheet.image_checksum,
    )
    return f"{path}?{urlencode({'access_token': token})}"


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

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
    payload = {
        "schema": TTS_CARD_EXPORT_SCHEMA,
        "collection": {
            "name": export.collection_name,
            "source": export.source_metadata,
        },
        "card_back_url": absolute_url(f"/card-images/{export.card_back_asset_path}"),
        "sheets": [
            {
                "sheet_id": sheet.sheet_id,
                "face_url": absolute_url(
                    f"/tts/card-sheets/{sheet.sheet_id}/image.webp"
                ),
                "columns": sheet.columns,
                "rows": sheet.rows,
                "revision": sheet.revision,
                "image_checksum": sheet.image_checksum,
            }
            for sheet in export.sheets
        ],
        "cards": [
            {
                "card_id": card.card_id,
                "card_version_id": card.card_version_id,
                "name": card.name,
                "quantity": card.quantity,
                "sheet_id": card.sheet_id,
                "slot_index": card.slot_index,
                "image_checksum": card.image_checksum,
            }
            for card in export.cards
        ],
        "skipped": [
            {
                "card_id": card.card_id,
                "name": card.name,
                "reason": card.reason,
            }
            for card in export.skipped
        ],
    }
    encoded_payload = base64.b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return EncodedTtsCardExport(
        encoded_payload=encoded_payload,
        exported_count=len(export.cards),
        skipped_count=len(export.skipped),
        sheet_count=len(export.sheets),
    )

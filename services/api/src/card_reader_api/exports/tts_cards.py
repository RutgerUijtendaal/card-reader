from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass

from card_reader_api.card_backs.serializers import card_back_image_url
from card_reader_api.cards.serializers import CardFilterParams
from card_reader_api.exports.serializers import TtsCardExportSource
from card_reader_core.models import CardVersionImage
from card_reader_core.repositories.cards import (
    CardListRow,
    get_latest_card_list_rows_by_card_ids,
    list_cards_for_content_version,
    list_matching_cards,
    resolve_image_file_path,
)
from card_reader_core.repositories.content_versions import get_content_version
from card_reader_core.services.card_backs import CardBackService

TTS_CARD_EXPORT_SCHEMA = "card-reader.tts-cards.v1"


@dataclass(frozen=True)
class TtsCardExportResult:
    encoded_payload: str
    exported_count: int
    skipped_count: int


@dataclass(frozen=True)
class ResolvedTtsCardSelection:
    collection_name: str
    source_metadata: dict[str, object]
    rows: list[CardListRow]
    skipped: list[dict[str, object]]


class TtsCardExportError(ValueError):
    def __init__(self, detail: str, *, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def build_tts_card_export(
    *,
    source: TtsCardExportSource,
    gallery_filters: CardFilterParams | None,
    absolute_url: Callable[[str], str],
) -> TtsCardExportResult:
    selection = _resolve_selection(source, gallery_filters=gallery_filters)
    card_back = CardBackService().get_current()
    relative_back_url = card_back_image_url(card_back) if card_back is not None else None
    if relative_back_url is None:
        raise TtsCardExportError("A usable current card back is required before exporting TTS cards.", status_code=409)

    cards: list[dict[str, object]] = []
    skipped = list(selection.skipped)
    for row in selection.rows:
        image = _first_usable_image(row)
        if image is None:
            skipped.append(
                {
                    "card_id": row.version.card.id,
                    "name": row.version.name,
                    "reason": "Card has no usable latest image.",
                }
            )
            continue
        cards.append(
            {
                "card_id": row.version.card.id,
                "card_version_id": row.version.id,
                "name": row.version.name,
                "quantity": 1,
                "front_url": absolute_url(f"/cards/{row.version.card.id}/image"),
                "image_checksum": image.checksum,
            }
        )

    if not cards:
        raise TtsCardExportError("No cards with usable latest images matched this export.")

    payload = {
        "schema": TTS_CARD_EXPORT_SCHEMA,
        "collection": {
            "name": selection.collection_name,
            "source": selection.source_metadata,
        },
        "card_back_url": absolute_url(relative_back_url),
        "cards": cards,
        "skipped": skipped,
    }
    encoded_payload = base64.b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return TtsCardExportResult(
        encoded_payload=encoded_payload,
        exported_count=len(cards),
        skipped_count=len(skipped),
    )


def _resolve_selection(
    source: TtsCardExportSource,
    *,
    gallery_filters: CardFilterParams | None,
) -> ResolvedTtsCardSelection:
    if source["type"] == "gallery":
        if gallery_filters is None:
            raise TtsCardExportError("Gallery filters are required for a gallery export.")
        return ResolvedTtsCardSelection(
            collection_name="Card Reader Gallery",
            source_metadata={
                "type": "gallery",
                "filters": {key: value for key, value in gallery_filters.items() if value is not None},
            },
            rows=list_matching_cards(**gallery_filters),
            skipped=[],
        )

    content_version_id = str(source["content_version_id"])
    content_version = get_content_version(content_version_id)
    if content_version is None:
        raise TtsCardExportError("Content version not found.", status_code=404)

    version_rows = list_cards_for_content_version(content_version_id)
    card_ids = list(dict.fromkeys(row.version.card.id for row in version_rows))
    rows = get_latest_card_list_rows_by_card_ids(card_ids)
    resolved_card_ids = {row.version.card.id for row in rows}
    skipped: list[dict[str, object]] = [
        {
            "card_id": row.version.card.id,
            "name": row.version.name,
            "reason": "Card has no latest version.",
        }
        for row in version_rows
        if row.version.card.id not in resolved_card_ids
    ]
    return ResolvedTtsCardSelection(
        collection_name=f"Card Reader {content_version.version_number}",
        source_metadata={
            "type": "content_version",
            "content_version_id": content_version.id,
            "version_number": content_version.version_number,
        },
        rows=rows,
        skipped=_deduplicate_skipped(skipped),
    )


def _first_usable_image(row: CardListRow) -> CardVersionImage | None:
    for image in row.version.images.all():
        if resolve_image_file_path(image) is not None:
            return image
    return None


def _deduplicate_skipped(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    out: list[dict[str, object]] = []
    for row in rows:
        card_id = str(row["card_id"])
        if card_id in seen:
            continue
        seen.add(card_id)
        out.append(row)
    return out

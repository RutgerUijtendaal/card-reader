from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from card_reader_core.models import (
    ACTIVE_CARD_LIFECYCLE_STATUS,
    ALL_CARD_LIFECYCLE_FILTER,
    CardVersionImage,
)
from card_reader_core.repositories.cards import (
    CARD_SORT_NAME_ASC,
    CardFilterParams,
    CardListRow,
    get_latest_card_list_rows_by_card_ids,
    list_cards_for_content_version,
    list_matching_cards,
)
from card_reader_core.repositories.content_versions import get_content_version
from card_reader_core.repositories.exports import get_tts_card_library_revision
from card_reader_core.repositories.tts_card_sheets import resolve_tts_card_image_path
from card_reader_core.services.card_backs import (
    CardBackService,
    resolve_card_back_image_asset_path,
)
from card_reader_core.services.tts_card_sheets import (
    TtsCardSheetPreparationError,
    TtsCardSheetService,
    get_tts_card_sheet_layout,
)


@dataclass(frozen=True)
class TtsCardExportCard:
    card_id: str
    card_version_id: str
    name: str
    quantity: int
    image_checksum: str
    sheet_id: str
    slot_index: int
    lifecycle_status: str


@dataclass(frozen=True)
class TtsCardExportSheet:
    sheet_id: str
    sequence: int
    columns: int
    rows: int
    revision: int
    image_checksum: str


@dataclass(frozen=True)
class TtsCardExportSkippedCard:
    card_id: str
    name: str
    reason: str


@dataclass(frozen=True)
class TtsCardExportData:
    collection_name: str
    source_metadata: dict[str, object]
    card_back_asset_path: str
    cards: list[TtsCardExportCard]
    sheets: list[TtsCardExportSheet]
    skipped: list[TtsCardExportSkippedCard]


class TtsCardExportErrorCode(StrEnum):
    CARD_BACK_UNAVAILABLE = "card_back_unavailable"
    CONTENT_VERSION_NOT_FOUND = "content_version_not_found"
    NO_USABLE_CARDS = "no_usable_cards"
    SHEETS_UNAVAILABLE = "sheets_unavailable"


class TtsCardExportError(ValueError):
    def __init__(self, code: TtsCardExportErrorCode, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class _ResolvedTtsCardSelection:
    collection_name: str
    source_metadata: dict[str, object]
    rows: list[CardListRow]
    skipped: list[TtsCardExportSkippedCard]


class TtsCardExportService:
    def get_library_revision(self) -> str:
        return get_tts_card_library_revision()

    def build_library_export(self) -> TtsCardExportData:
        selection = _ResolvedTtsCardSelection(
            collection_name="Card Reader Library",
            source_metadata={
                "type": "library",
                "lifecycle_status": ALL_CARD_LIFECYCLE_FILTER,
            },
            rows=list_matching_cards(
                query=None,
                max_confidence=None,
                lifecycle_status=ALL_CARD_LIFECYCLE_FILTER,
                sort=CARD_SORT_NAME_ASC,
            ),
            skipped=[],
        )
        return self._build_export(selection)

    def build_gallery_export(self, filters: CardFilterParams) -> TtsCardExportData:
        selection = _ResolvedTtsCardSelection(
            collection_name="Card Reader Gallery",
            source_metadata={
                "type": "gallery",
                "filters": {key: value for key, value in filters.items() if value is not None},
            },
            rows=list_matching_cards(**filters),
            skipped=[],
        )
        return self._build_export(selection)

    def build_content_version_export(self, content_version_id: str) -> TtsCardExportData:
        content_version = get_content_version(content_version_id)
        if content_version is None:
            raise TtsCardExportError(
                TtsCardExportErrorCode.CONTENT_VERSION_NOT_FOUND,
                "Content version not found.",
            )

        version_rows = list_cards_for_content_version(
            content_version_id,
            lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
        )
        card_ids = list(dict.fromkeys(row.version.card.id for row in version_rows))
        rows = get_latest_card_list_rows_by_card_ids(
            card_ids,
            lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
        )
        resolved_card_ids = {row.version.card.id for row in rows}
        skipped = _deduplicate_skipped(
            [
                TtsCardExportSkippedCard(
                    card_id=row.version.card.id,
                    name=row.version.name,
                    reason="Card has no latest version.",
                )
                for row in version_rows
                if row.version.card.id not in resolved_card_ids
            ]
        )
        return self._build_export(
            _ResolvedTtsCardSelection(
                collection_name=f"Card Reader {content_version.version_number}",
                source_metadata={
                    "type": "content_version",
                    "content_version_id": content_version.id,
                    "version_number": content_version.version_number,
                },
                rows=rows,
                skipped=skipped,
            )
        )

    def _build_export(self, selection: _ResolvedTtsCardSelection) -> TtsCardExportData:
        card_back = CardBackService().get_current()
        card_back_asset_path = (
            resolve_card_back_image_asset_path(card_back) if card_back is not None else None
        )
        if card_back_asset_path is None:
            raise TtsCardExportError(
                TtsCardExportErrorCode.CARD_BACK_UNAVAILABLE,
                "A usable current card back is required before exporting TTS cards.",
            )

        usable_rows: list[tuple[CardListRow, CardVersionImage]] = []
        skipped = list(selection.skipped)
        for row in selection.rows:
            image = _first_usable_image(row)
            if image is None:
                skipped.append(
                    TtsCardExportSkippedCard(
                        card_id=row.version.card.id,
                        name=row.version.name,
                        reason="Card has no usable latest image.",
                    )
                )
                continue
            usable_rows.append((row, image))

        if not usable_rows:
            raise TtsCardExportError(
                TtsCardExportErrorCode.NO_USABLE_CARDS,
                "No cards with usable latest images matched this export.",
            )

        card_ids = [row.version.card.id for row, _image in usable_rows]
        try:
            assignments = TtsCardSheetService().prepare_cards(card_ids)
        except TtsCardSheetPreparationError as exc:
            raise TtsCardExportError(
                TtsCardExportErrorCode.SHEETS_UNAVAILABLE,
                str(exc),
            ) from exc

        cards: list[TtsCardExportCard] = []
        for row, image in usable_rows:
            assignment = assignments.get(row.version.card.id)
            if assignment is None:
                skipped.append(
                    TtsCardExportSkippedCard(
                        card_id=row.version.card.id,
                        name=row.version.name,
                        reason="Card has no TTS sheet assignment.",
                    )
                )
                continue
            cards.append(
                TtsCardExportCard(
                    card_id=row.version.card.id,
                    card_version_id=row.version.id,
                    name=row.version.name,
                    quantity=1,
                    image_checksum=assignment.image_checksum,
                    sheet_id=assignment.sheet_id,
                    slot_index=assignment.slot_index,
                    lifecycle_status=row.version.card.lifecycle_status,
                )
            )

        if not cards:
            raise TtsCardExportError(
                TtsCardExportErrorCode.NO_USABLE_CARDS,
                "No cards with usable TTS sheet assignments matched this export.",
            )

        exported_card_ids = {card.card_id for card in cards}
        sheet_assignments = {
            assignment.sheet_id: assignment
            for assignment in assignments.values()
            if assignment.card_id in exported_card_ids
        }
        sheets = [
            TtsCardExportSheet(
                sheet_id=assignment.sheet_id,
                sequence=assignment.sheet_sequence,
                columns=get_tts_card_sheet_layout(assignment.layout_version).columns,
                rows=get_tts_card_sheet_layout(assignment.layout_version).rows,
                revision=assignment.rendered_revision,
                image_checksum=assignment.rendered_checksum,
            )
            for assignment in sorted(
                sheet_assignments.values(), key=lambda value: value.sheet_sequence
            )
        ]
        return TtsCardExportData(
            collection_name=selection.collection_name,
            source_metadata=selection.source_metadata,
            card_back_asset_path=card_back_asset_path,
            cards=cards,
            sheets=sheets,
            skipped=skipped,
        )


def _first_usable_image(row: CardListRow) -> CardVersionImage | None:
    for image in row.version.images.all():
        if resolve_tts_card_image_path(image) is not None:
            return image
    return None


def _deduplicate_skipped(
    rows: list[TtsCardExportSkippedCard],
) -> list[TtsCardExportSkippedCard]:
    seen: set[str] = set()
    out: list[TtsCardExportSkippedCard] = []
    for row in rows:
        if row.card_id in seen:
            continue
        seen.add(row.card_id)
        out.append(row)
    return out

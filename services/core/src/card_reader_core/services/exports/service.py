from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from card_reader_core.models import (
    ACTIVE_CARD_LIFECYCLE_STATUS,
    ALL_CARD_LIFECYCLE_FILTER,
    PLAYER_CARD_POOL,
    CardVersionImage,
)
from card_reader_core.repositories.cards import (
    CardFilterParams,
    CardListRow,
    get_latest_card_list_rows_by_card_ids,
    list_cards_for_content_version,
    list_matching_cards,
)
from card_reader_core.repositories.content_versions import get_content_version
from card_reader_core.repositories.decks import get_deck_export_snapshot
from card_reader_core.repositories.tts_card_sheets import resolve_tts_card_image_path
from card_reader_core.services.card_backs import (
    resolve_card_back_image_asset_path,
    resolve_effective_card_backs,
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
    role: str | None
    card_back_id: str


@dataclass(frozen=True)
class TtsCardExportCardBack:
    card_back_id: str
    image_checksum: str
    asset_path: str


@dataclass(frozen=True)
class TtsCardExportSheet:
    sheet_id: str
    card_pool: str
    sequence: int
    columns: int
    rows: int
    revision: int
    image_checksum: str


@dataclass(frozen=True)
class TtsCardExportSkippedCard:
    card_id: str
    name: str
    quantity: int
    reason: str
    role: str | None


@dataclass(frozen=True)
class TtsCardExportData:
    collection_name: str
    collection_description: str | None
    source_metadata: dict[str, object]
    card_backs: list[TtsCardExportCardBack]
    cards: list[TtsCardExportCard]
    sheets: list[TtsCardExportSheet]
    skipped: list[TtsCardExportSkippedCard]


class TtsCardExportErrorCode(StrEnum):
    CARD_BACK_UNAVAILABLE = "card_back_unavailable"
    CONTENT_VERSION_NOT_FOUND = "content_version_not_found"
    DECK_SOURCE_NOT_FOUND = "deck_source_not_found"
    NO_USABLE_CARDS = "no_usable_cards"
    REQUIRED_CARD_UNAVAILABLE = "required_card_unavailable"
    SHEETS_UNAVAILABLE = "sheets_unavailable"


class TtsCardExportError(ValueError):
    def __init__(self, code: TtsCardExportErrorCode, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class _ResolvedTtsCardSelectionEntry:
    row: CardListRow
    quantity: int
    role: str | None
    required: bool = False


@dataclass(frozen=True)
class _ResolvedTtsCardSelection:
    collection_name: str
    collection_description: str | None
    source_metadata: dict[str, object]
    entries: list[_ResolvedTtsCardSelectionEntry]
    skipped: list[TtsCardExportSkippedCard]
    require_player_cards: bool = False


class TtsCardExportService:
    def build_gallery_export(
        self,
        filters: CardFilterParams,
    ) -> TtsCardExportData:
        selection = _ResolvedTtsCardSelection(
            collection_name="Card Reader Gallery",
            collection_description=None,
            source_metadata={
                "type": "gallery",
                "filters": {key: value for key, value in filters.items() if value is not None},
            },
            entries=_selection_entries(list_matching_cards(**filters)),
            skipped=[],
        )
        return self._build_export(selection)

    def build_content_version_export(
        self,
        content_version_id: str,
    ) -> TtsCardExportData:
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
                    quantity=1,
                    reason="Card has no latest version.",
                    role=None,
                )
                for row in version_rows
                if row.version.card.id not in resolved_card_ids
            ]
        )
        return self._build_export(
            _ResolvedTtsCardSelection(
                collection_name=f"Card Reader {content_version.version_number}",
                collection_description=None,
                source_metadata={
                    "type": "content_version",
                    "content_version_id": content_version.id,
                    "version_number": content_version.version_number,
                },
                entries=_selection_entries(rows),
                skipped=skipped,
            ),
        )

    def build_deck_export(
        self,
        deck_id: str,
        *,
        sideboard_id: str | None = None,
    ) -> TtsCardExportData:
        snapshot = get_deck_export_snapshot(deck_id, sideboard_id=sideboard_id)
        if snapshot is None:
            detail = "Sideboard not found" if sideboard_id is not None else "Deck not found"
            raise TtsCardExportError(TtsCardExportErrorCode.DECK_SOURCE_NOT_FOUND, detail)

        rows = get_latest_card_list_rows_by_card_ids(
            [entry.card_id for entry in snapshot.entries],
            lifecycle_status=ALL_CARD_LIFECYCLE_FILTER,
        )
        rows_by_card_id = {row.version.card.id: row for row in rows}
        entries: list[_ResolvedTtsCardSelectionEntry] = []
        skipped: list[TtsCardExportSkippedCard] = []
        for requested_entry in snapshot.entries:
            row = rows_by_card_id.get(requested_entry.card_id)
            if row is None:
                if requested_entry.required:
                    raise _required_card_unavailable(
                        requested_entry.card_name,
                        "has no latest version",
                    )
                skipped.append(
                    TtsCardExportSkippedCard(
                        card_id=requested_entry.card_id,
                        name=requested_entry.card_name,
                        quantity=requested_entry.quantity,
                        reason="Card has no latest version.",
                        role=requested_entry.role,
                    )
                )
                continue
            entries.append(
                _ResolvedTtsCardSelectionEntry(
                    row=row,
                    quantity=requested_entry.quantity,
                    role=requested_entry.role,
                    required=requested_entry.required,
                )
            )

        source_metadata: dict[str, object] = {
            "type": "deck",
            "deck_id": snapshot.deck_id,
            "scope": snapshot.scope,
            "hero_card_id": snapshot.hero_card_id,
            "difficulty": snapshot.difficulty,
            "tags": [
                {
                    "id": tag.id,
                    "key": tag.key,
                    "label": tag.label,
                    "kind": tag.kind,
                }
                for tag in snapshot.tags
            ],
        }
        if snapshot.sideboard_id is not None:
            source_metadata["sideboard_id"] = snapshot.sideboard_id
            source_metadata["sideboard_name"] = snapshot.sideboard_name

        return self._build_export(
            _ResolvedTtsCardSelection(
                collection_name=snapshot.collection_name,
                collection_description=snapshot.collection_description,
                source_metadata=source_metadata,
                entries=entries,
                skipped=skipped,
                require_player_cards=True,
            ),
        )

    def _build_export(
        self,
        selection: _ResolvedTtsCardSelection,
    ) -> TtsCardExportData:
        if selection.require_player_cards and any(
            entry.row.version.card.card_pool != PLAYER_CARD_POOL
            for entry in selection.entries
        ):
            raise _deck_source_unavailable()

        usable_entries: list[tuple[_ResolvedTtsCardSelectionEntry, CardVersionImage]] = []
        skipped = list(selection.skipped)
        for entry in selection.entries:
            row = entry.row
            image = _first_usable_image(row)
            if image is None:
                if entry.required:
                    raise _required_card_unavailable(row.version.name, "has no usable latest image")
                skipped.append(
                    TtsCardExportSkippedCard(
                        card_id=row.version.card.id,
                        name=row.version.name,
                        quantity=entry.quantity,
                        reason="Card has no usable latest image.",
                        role=entry.role,
                    )
                )
                continue
            usable_entries.append((entry, image))

        if not usable_entries:
            raise TtsCardExportError(
                TtsCardExportErrorCode.NO_USABLE_CARDS,
                "No cards with usable latest images matched this export.",
            )

        card_ids = [entry.row.version.card.id for entry, _image in usable_entries]
        resolved_card_backs = resolve_effective_card_backs(card_ids)
        card_back_resources: dict[str, TtsCardExportCardBack] = {}
        card_back_ids_by_card_id: dict[str, str] = {}
        for entry, _image in usable_entries:
            card = entry.row.version.card
            resolved = resolved_card_backs.get(card.id)
            card_back = resolved.card_back if resolved is not None else None
            asset_path = (
                resolve_card_back_image_asset_path(card_back)
                if card_back is not None
                else None
            )
            if card_back is None or asset_path is None:
                raise TtsCardExportError(
                    TtsCardExportErrorCode.CARD_BACK_UNAVAILABLE,
                    f"Card '{entry.row.version.name}' ({card.id}) in pool "
                    f"'{card.card_pool}' has no usable effective card back.",
                )
            card_back_resources[card_back.id] = TtsCardExportCardBack(
                card_back_id=card_back.id,
                image_checksum=card_back.checksum,
                asset_path=asset_path,
            )
            card_back_ids_by_card_id[card.id] = card_back.id

        try:
            assignments = TtsCardSheetService().prepare_cards(card_ids)
        except TtsCardSheetPreparationError as exc:
            raise TtsCardExportError(
                TtsCardExportErrorCode.SHEETS_UNAVAILABLE,
                str(exc),
            ) from exc

        cards: list[TtsCardExportCard] = []
        for entry, image in usable_entries:
            row = entry.row
            assignment = assignments.get(row.version.card.id)
            if assignment is None:
                if entry.required:
                    raise _required_card_unavailable(
                        row.version.name,
                        "has no TTS sheet assignment",
                    )
                skipped.append(
                    TtsCardExportSkippedCard(
                        card_id=row.version.card.id,
                        name=row.version.name,
                        quantity=entry.quantity,
                        reason="Card has no TTS sheet assignment.",
                        role=entry.role,
                    )
                )
                continue
            cards.append(
                TtsCardExportCard(
                    card_id=row.version.card.id,
                    card_version_id=row.version.id,
                    name=row.version.name,
                    quantity=entry.quantity,
                    image_checksum=assignment.image_checksum,
                    sheet_id=assignment.sheet_id,
                    slot_index=assignment.slot_index,
                    lifecycle_status=row.version.card.lifecycle_status,
                    role=entry.role,
                    card_back_id=card_back_ids_by_card_id[row.version.card.id],
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
                card_pool=assignment.card_pool,
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
            collection_description=selection.collection_description,
            source_metadata=selection.source_metadata,
            card_backs=list(card_back_resources.values()),
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
    seen: set[tuple[str, str | None]] = set()
    out: list[TtsCardExportSkippedCard] = []
    for row in rows:
        key = (row.card_id, row.role)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _selection_entries(rows: list[CardListRow]) -> list[_ResolvedTtsCardSelectionEntry]:
    return [_ResolvedTtsCardSelectionEntry(row=row, quantity=1, role=None) for row in rows]


def _required_card_unavailable(name: str, reason: str) -> TtsCardExportError:
    return TtsCardExportError(
        TtsCardExportErrorCode.REQUIRED_CARD_UNAVAILABLE,
        f"Required deck hero '{name}' {reason}.",
    )


def _deck_source_unavailable() -> TtsCardExportError:
    return TtsCardExportError(
        TtsCardExportErrorCode.DECK_SOURCE_NOT_FOUND,
        "Deck not found",
    )

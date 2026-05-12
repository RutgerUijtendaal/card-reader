from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from card_reader_core.models import Card, CardVersion, CardVersionImage, Keyword, ParseResult, Symbol, Tag, Type
from card_reader_core.repositories.cards_repository import (
    FieldSourcesPayload,
    PaginatedCardList,
    ParsedSnapshotPayload,
    decode_field_sources,
    decode_parsed_snapshot,
    get_card,
    get_card_image,
    get_latest_card_version,
    get_parse_result,
    list_card_generations,
    list_cards,
    resolve_image_file_path,
    update_card,
    update_latest_card_version,
)
from card_reader_core.repositories.metadata_repository import (
    get_keywords_for_card_version,
    get_keywords_for_card_versions,
    get_symbols_for_card_version,
    get_symbols_for_card_versions,
    get_tags_for_card_version,
    get_tags_for_card_versions,
    get_types_for_card_version,
    get_types_for_card_versions,
    list_keywords,
    list_symbols,
    list_tags,
    list_types,
)


class CardMetadata(TypedDict):
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


class CardEditState(TypedDict):
    field_sources: FieldSourcesPayload
    parsed_snapshot: ParsedSnapshotPayload
    parse_result: ParseResult | None


class CardService:
    def list_cards(self, **filters: Any) -> PaginatedCardList:
        return list_cards(**filters)

    def list_card_generations(self, card_id: str) -> list[CardVersion]:
        return list_card_generations(card_id)

    def get_filter_metadata(self) -> CardMetadata:
        return {
            "keywords": list_keywords(),
            "tags": list_tags(),
            "symbols": list_symbols(),
            "types": list_types(),
        }

    def get_card_with_image(
        self,
        card_id: str,
    ) -> tuple[Card | None, CardVersion | None, CardVersionImage | None]:
        card = get_card(card_id)
        if card is None:
            return None, None, None
        version = get_latest_card_version(card_id)
        if version is None:
            return card, None, None
        image = get_card_image(version.id)
        return card, version, image

    def get_card(self, card_id: str) -> Card | None:
        return get_card(card_id)

    def get_card_image(self, card_version_id: str) -> CardVersionImage | None:
        return get_card_image(card_version_id)

    def resolve_card_image_path(self, image: CardVersionImage) -> Path | None:
        return resolve_image_file_path(image)

    def get_card_version_metadata(self, card_version_id: str) -> CardMetadata:
        return {
            "keywords": get_keywords_for_card_version(card_version_id),
            "tags": get_tags_for_card_version(card_version_id),
            "symbols": get_symbols_for_card_version(card_version_id),
            "types": get_types_for_card_version(card_version_id),
        }

    def get_card_versions_metadata(self, card_version_ids: list[str]) -> dict[str, CardMetadata]:
        keywords = get_keywords_for_card_versions(card_version_ids)
        tags = get_tags_for_card_versions(card_version_ids)
        symbols = get_symbols_for_card_versions(card_version_ids)
        types = get_types_for_card_versions(card_version_ids)
        return {
            card_version_id: {
                "keywords": keywords.get(card_version_id, []),
                "tags": tags.get(card_version_id, []),
                "symbols": symbols.get(card_version_id, []),
                "types": types.get(card_version_id, []),
            }
            for card_version_id in card_version_ids
        }

    def get_card_version_edit_state(self, version: CardVersion) -> CardEditState:
        return {
            "field_sources": decode_field_sources(version.field_sources_json),
            "parsed_snapshot": decode_parsed_snapshot(version.parsed_snapshot_json),
            "parse_result": get_parse_result(version.parse_result_id),
        }

    def update_card(
        self,
        *,
        card_id: str,
        name: str | None,
        type_line: str | None,
        mana_cost: str | None,
        rules_text: str | None,
    ) -> tuple[Card, CardVersion] | None:
        return update_card(
            card_id=card_id,
            name=name,
            type_line=type_line,
            mana_cost=mana_cost,
            rules_text=rules_text,
        )

    def update_latest_card_version(
        self,
        *,
        card_id: str,
        updates: dict[str, object],
        restore_fields: list[str],
        restore_metadata_groups: list[str],
        unlock_fields: list[str],
        unlock_metadata_groups: list[str],
    ) -> tuple[Card, CardVersion] | None:
        return update_latest_card_version(
            card_id=card_id,
            updates=updates,
            restore_fields=restore_fields,
            restore_metadata_groups=restore_metadata_groups,
            unlock_fields=unlock_fields,
            unlock_metadata_groups=unlock_metadata_groups,
        )

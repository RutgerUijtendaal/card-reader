from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from card_reader_core.models import Card, CardVersion, CardVersionImage, Keyword, ParseResult, Symbol, Tag, Type
from card_reader_core.repositories.cards_repository import (
    FieldSourcesPayload,
    ParsedSnapshotPayload,
    decode_field_sources,
    decode_parsed_snapshot,
    get_card,
    get_card_image,
    get_latest_card_version,
    resolve_image_file_path,
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


def get_filter_metadata() -> CardMetadata:
    return {
        "keywords": list_keywords(),
        "tags": list_tags(),
        "symbols": list_symbols(),
        "types": list_types(),
    }


def get_card_with_image(card_id: str) -> tuple[Card | None, CardVersion | None, CardVersionImage | None]:
    card = get_card(card_id)
    if card is None:
        return None, None, None
    version = get_latest_card_version(card_id)
    if version is None:
        return card, None, None
    image = get_card_image(version.id)
    return card, version, image


def resolve_card_image_path(image: CardVersionImage) -> Path | None:
    return resolve_image_file_path(image)


def get_card_version_metadata(card_version_id: str) -> CardMetadata:
    return {
        "keywords": get_keywords_for_card_version(card_version_id),
        "tags": get_tags_for_card_version(card_version_id),
        "symbols": get_symbols_for_card_version(card_version_id),
        "types": get_types_for_card_version(card_version_id),
    }


def get_card_versions_metadata(card_version_ids: list[str]) -> dict[str, CardMetadata]:
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


def get_card_version_edit_state(version: CardVersion) -> CardEditState:
    return {
        "field_sources": decode_field_sources(version.field_sources_json),
        "parsed_snapshot": decode_parsed_snapshot(version.parsed_snapshot_json),
        "parse_result": version.parse_result,
    }

from __future__ import annotations

import json

from card_reader_core.models import Keyword, Tag, Type

from card_reader_parser.extractors.known_metadata_extractor import KnownMetadataExtractor


def test_extract_ids_matches_label_case_insensitively() -> None:
    extractor = KnownMetadataExtractor()
    keyword = Keyword(id="keyword-1", key="turn-start", label="Turn Start", identifiers_json='["turn start"]')

    matched = extractor.extract_ids("At TURN START, draw a card.", [keyword])

    assert matched == ["keyword-1"]


def test_extract_ids_matches_identifiers_case_insensitively() -> None:
    extractor = KnownMetadataExtractor()
    keyword = Keyword(
        id="keyword-1",
        key="turn-start",
        label="Turn Start",
        identifiers_json=json.dumps(["turn start", "at the beginning of your turn"]),
    )

    matched = extractor.extract_ids("AT THE BEGINNING OF YOUR TURN, draw a card.", [keyword])

    assert matched == ["keyword-1"]


def test_extract_ids_returns_only_known_tag_matches() -> None:
    extractor = KnownMetadataExtractor()
    known_tag = Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json='["weapon"]')

    matched = extractor.extract_ids("Silver Weapon Unknown", [known_tag])

    assert matched == ["tag-1"]


def test_extract_ids_supports_multi_word_type_identifiers() -> None:
    extractor = KnownMetadataExtractor()
    known_type = Type(
        id="type-1",
        key="persistent",
        label="Persistent",
        identifiers_json=json.dumps(["persistent", "persistent spell"]),
    )

    matched = extractor.extract_ids("Persistent Spell", [known_type])

    assert matched == ["type-1"]

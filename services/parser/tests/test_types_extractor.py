from __future__ import annotations

from card_reader_parser.extractors.types_extractor import TypesExtractor


def test_extract_splits_type_part_on_whitespace() -> None:
    extractor = TypesExtractor()

    assert extractor.extract("Unique Goblin Ally - Warrior") == ["Unique", "Goblin", "Ally"]


def test_extract_dedupes_types_case_insensitively() -> None:
    extractor = TypesExtractor()

    assert extractor.extract("Goblin goblin Hero") == ["Goblin", "Hero"]

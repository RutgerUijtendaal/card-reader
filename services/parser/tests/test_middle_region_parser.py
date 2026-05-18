from __future__ import annotations

from PIL import Image

from card_reader_core.models import Tag, Type
from card_reader_parser.extractors.known_metadata_extractor import KnownMetadataExtractor
from card_reader_parser.parsers.regions.middle_region_parser import MiddleRegionParser


class StubOcrRunner:
    def __init__(self, text: str) -> None:
        self._text = text

    def run(self, _image: Image.Image) -> dict[str, object]:
        return {
            "text": self._text,
            "confidence": 0.88,
            "lines": [{"text": self._text, "confidence": 0.88}],
        }


def test_split_middle_text_handles_empty_and_missing_hyphen() -> None:
    parser = MiddleRegionParser(StubOcrRunner(""), KnownMetadataExtractor())

    assert parser._split_middle_text("") == ("", "")
    assert parser._split_middle_text(" Persistent Spell ") == ("Persistent Spell", "")


def test_split_middle_text_normalizes_spacing_around_hyphen() -> None:
    parser = MiddleRegionParser(StubOcrRunner(""), KnownMetadataExtractor())

    assert parser._split_middle_text("  Persistent   Spell   -   Silver   Weapon ") == (
        "Persistent Spell",
        "Silver Weapon",
    )


def test_split_middle_text_does_not_split_on_hyphen_without_surrounding_spaces() -> None:
    parser = MiddleRegionParser(StubOcrRunner(""), KnownMetadataExtractor())

    assert parser._split_middle_text("Sword-and-Shield Relic") == ("Sword-and-Shield Relic", "")
    assert parser._split_middle_text("Persistent-Weapon") == ("Persistent-Weapon", "")


def test_middle_region_parser_matches_known_type_and_tag_without_suggestions() -> None:
    parser = MiddleRegionParser(StubOcrRunner("Persistent Spell - Silver Weapon"), KnownMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["silver weapon"])],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent spell"])],
    )

    assert result.extracted_type_ids == ["type-1"]
    assert result.extracted_tag_ids == ["tag-1"]
    assert result.extracted_type_suggestions == []
    assert result.extracted_tag_suggestions == []


def test_middle_region_parser_emits_type_suggestion_for_unknown_leftover() -> None:
    parser = MiddleRegionParser(StubOcrRunner("Persistent Spell Mystery - Weapon"), KnownMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["weapon"])],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent spell"])],
    )

    assert result.extracted_type_ids == ["type-1"]
    assert [row.normalized_value for row in result.extracted_type_suggestions] == ["mystery"]
    assert result.extracted_tag_suggestions == []


def test_middle_region_parser_removes_commas_from_type_suggestions() -> None:
    parser = MiddleRegionParser(StubOcrRunner("Persistent Spell, Mystery - Weapon"), KnownMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["weapon"])],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent spell"])],
    )

    assert result.extracted_type_ids == ["type-1"]
    assert [row.normalized_value for row in result.extracted_type_suggestions] == ["mystery"]


def test_middle_region_parser_emits_tag_suggestion_for_unknown_right_side() -> None:
    parser = MiddleRegionParser(StubOcrRunner("Persistent - Silver Weapon Relic"), KnownMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["silver weapon"])],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent"])],
    )

    assert result.extracted_tag_ids == ["tag-1"]
    assert [row.normalized_value for row in result.extracted_tag_suggestions] == ["relic"]


def test_middle_region_parser_splits_unknown_tag_leftovers_by_whitespace_when_no_commas_exist() -> None:
    parser = MiddleRegionParser(StubOcrRunner("Persistent - Silver Weapon Relic Ancient"), KnownMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["silver weapon"])],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent"])],
    )

    assert result.extracted_tag_ids == ["tag-1"]
    assert [row.normalized_value for row in result.extracted_tag_suggestions] == ["relic", "ancient"]


def test_middle_region_parser_splits_unknown_tag_leftovers_by_commas_when_present() -> None:
    parser = MiddleRegionParser(
        StubOcrRunner("Persistent - Silver Weapon, Relic, Ancient Artifact"),
        KnownMetadataExtractor(),
    )
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["silver weapon"])],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent"])],
    )

    assert result.extracted_tag_ids == ["tag-1"]
    assert [row.normalized_value for row in result.extracted_tag_suggestions] == [
        "relic",
        "ancient artifact",
    ]


def test_middle_region_parser_ignores_comma_only_tag_leftovers_after_known_matches() -> None:
    parser = MiddleRegionParser(
        StubOcrRunner("Persistent - Silver Weapon, Ancient Artifact, Weapon"),
        KnownMetadataExtractor(),
    )
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[
            Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["silver weapon", "weapon"]),
            Tag(id="tag-2", key="ancient-artifact", label="Ancient Artifact", identifiers_json=["ancient artifact"]),
        ],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent"])],
    )

    assert result.extracted_tag_ids == ["tag-1", "tag-2"]
    assert result.extracted_tag_suggestions == []


def test_middle_region_parser_emits_suggestion_when_no_known_match_exists() -> None:
    parser = MiddleRegionParser(StubOcrRunner("Mystic Relic"), KnownMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent"])],
    )

    assert result.extracted_type_ids == []
    assert [row.normalized_value for row in result.extracted_type_suggestions] == ["mystic relic"]
    assert result.extracted_tag_suggestions == []


def test_middle_region_parser_deduplicates_repeated_known_identifier_matches() -> None:
    parser = MiddleRegionParser(StubOcrRunner("Persistent Persistent - Weapon Weapon"), KnownMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["weapon"])],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent"])],
    )

    assert result.extracted_type_ids == ["type-1"]
    assert result.extracted_tag_ids == ["tag-1"]
    assert result.extracted_type_suggestions == []
    assert result.extracted_tag_suggestions == []


def test_middle_region_parser_treats_added_identifier_as_reparse_equivalent() -> None:
    parser = MiddleRegionParser(StubOcrRunner("Persistent Spell Mystery - Weapon"), KnownMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    initial = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["weapon"])],
        known_types=[Type(id="type-1", key="persistent", label="Persistent", identifiers_json=["persistent spell"])],
    )
    reparsed = parser.parse(
        region_name="type_bar",
        image=image,
        region_spec={},
        known_tags=[Tag(id="tag-1", key="weapon", label="Weapon", identifiers_json=["weapon"])],
        known_types=[
            Type(
                id="type-1",
                key="persistent",
                label="Persistent",
                identifiers_json=["persistent spell", "persistent spell mystery"],
            )
        ],
    )

    assert [row.normalized_value for row in initial.extracted_type_suggestions] == ["mystery"]
    assert reparsed.extracted_type_suggestions == []

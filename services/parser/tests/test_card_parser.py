from __future__ import annotations

from pathlib import Path

from PIL import Image

from card_reader_parser.parsers.card_parser import CardParser
from card_reader_parser.parsers.region_cropper import RegionCrop
from card_reader_parser.parsers.regions import RegionParseResult


class StubTemplateService:
    def __init__(self, template: dict[str, object]) -> None:
        self.template = template

    def get_template_definition(self, _template_id: str) -> dict[str, object]:
        return self.template


class StubCropper:
    def __init__(self, region_ids: list[str]) -> None:
        self.region_ids = region_ids

    def crop_regions(self, *, image_path: Path, template: dict[str, object]) -> dict[str, RegionCrop]:
        _ = image_path
        _ = template
        return {
            region_id: {
                "image": Image.new("RGB", (10, 10), "white"),
                "x": 0,
                "y": 0,
                "w": 10,
                "h": 10,
            }
            for region_id in self.region_ids
        }

    def write_debug_crops(self, **_: object) -> None:
        return None


class StubRegionParser:
    def __init__(self, results: dict[str, RegionParseResult]) -> None:
        self.results = results
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> RegionParseResult:
        self.calls.append(kwargs)
        region_name = str(kwargs["region_name"])
        return self.results[region_name]


def _parser_result(
    region_name: str,
    *,
    text: str = "",
    confidence: float = 0.0,
    normalized_fields: dict[str, str] | None = None,
) -> RegionParseResult:
    return RegionParseResult(
        region_name=region_name,
        text=text,
        confidence=confidence,
        normalized_fields=normalized_fields or {},
    )


def _build_parser(*, template: dict[str, object], region_ids: list[str]) -> CardParser:
    parser = CardParser.__new__(CardParser)
    parser._template_service = StubTemplateService(template)
    parser._cropper = StubCropper(region_ids)
    parser._name_mana_cost_parser = StubRegionParser(
        {"top_bar": _parser_result("top_bar", text="Top", confidence=0.91, normalized_fields={"name": "Spellblade"})}
    )
    parser._type_tag_parser = StubRegionParser(
        {
            "type_bar": _parser_result(
                "type_bar",
                text="Equipment - Weapon",
                confidence=0.82,
                normalized_fields={"type_line": "Equipment - Weapon"},
            )
        }
    )
    parser._rules_text_parser = StubRegionParser(
        {
            "rules_text": _parser_result(
                "rules_text",
                text="Primary rules",
                confidence=0.77,
                normalized_fields={"rules_text": "Primary rules"},
            ),
            "rules_text_fallback": _parser_result(
                "rules_text_fallback",
                text="Fallback rules",
                confidence=0.66,
                normalized_fields={"rules_text": "Fallback rules"},
            ),
        }
    )
    parser._affinity_parser = StubRegionParser(
        {
            "bottom_middle": _parser_result(
                "bottom_middle",
                text="Affinity",
                confidence=0.73,
                normalized_fields={"mana_symbols": "{A}"},
            )
        }
    )
    parser._stats_region_parser = StubRegionParser(
        {
            "bottom_left": _parser_result(
                "bottom_left",
                text="3",
                confidence=0.69,
                normalized_fields={"attack": "3"},
            ),
            "bottom_right": _parser_result(
                "bottom_right",
                text="2",
                confidence=0.64,
                normalized_fields={"health": "2"},
            ),
        }
    )
    return parser


def test_card_parser_dispatches_parser_type_handlers(tmp_path: Path) -> None:
    image_path = tmp_path / "card.png"
    image_path.write_bytes(b"card-image")
    template = {
        "regions": [
            {"region_id": "top_bar", "parser_type": "name_mana_cost", "cut_region": {}, "ocr_config": {}},
            {"region_id": "type_bar", "parser_type": "type_tag", "cut_region": {}, "ocr_config": {}},
            {"region_id": "rules_text", "parser_type": "rules_text", "cut_region": {}, "ocr_config": {}},
            {"region_id": "bottom_left", "parser_type": "attack", "cut_region": {}, "ocr_config": {}},
            {"region_id": "bottom_middle", "parser_type": "affinity", "cut_region": {}, "ocr_config": {}},
            {"region_id": "bottom_right", "parser_type": "health", "cut_region": {}, "ocr_config": {}},
        ]
    }
    parser = _build_parser(
        template=template,
        region_ids=["top_bar", "type_bar", "rules_text", "bottom_left", "bottom_middle", "bottom_right"],
    )

    parsed = parser.parse(image_path=image_path, template_id="mtg-like-v1")

    assert len(parser._name_mana_cost_parser.calls) == 1
    assert len(parser._type_tag_parser.calls) == 1
    assert len(parser._rules_text_parser.calls) == 1
    assert len(parser._affinity_parser.calls) == 1
    assert len(parser._stats_region_parser.calls) == 2
    assert parser._stats_region_parser.calls[0]["field_name"] == "attack"
    assert parser._stats_region_parser.calls[1]["field_name"] == "health"
    assert parsed.normalized_fields["name"] == "Spellblade"
    assert parsed.normalized_fields["type_line"] == "Equipment - Weapon"
    assert parsed.normalized_fields["rules_text"] == "Primary rules"
    assert parsed.normalized_fields["attack"] == "3"
    assert parsed.normalized_fields["health"] == "2"


def test_card_parser_uses_second_rules_text_region_as_fallback(tmp_path: Path) -> None:
    image_path = tmp_path / "card.png"
    image_path.write_bytes(b"card-image")
    template = {
        "regions": [
            {"region_id": "rules_text", "parser_type": "rules_text", "cut_region": {}, "ocr_config": {}},
            {"region_id": "rules_text_fallback", "parser_type": "rules_text", "cut_region": {}, "ocr_config": {}},
        ]
    }
    parser = _build_parser(template=template, region_ids=["rules_text", "rules_text_fallback"])
    parser._rules_text_parser = StubRegionParser(
        {
            "rules_text": _parser_result("rules_text", text="", confidence=0.25, normalized_fields={}),
            "rules_text_fallback": _parser_result(
                "rules_text_fallback",
                text="Recovered rules",
                confidence=0.61,
                normalized_fields={"rules_text": "Recovered rules"},
            ),
        }
    )

    parsed = parser.parse(image_path=image_path, template_id="mtg-like-v1")

    assert len(parser._rules_text_parser.calls) == 2
    assert parsed.normalized_fields["rules_text"] == "Recovered rules"
    assert parsed.confidence["rules_text"] == 0.61

from __future__ import annotations

from typing import Any

from PIL import Image

from card_reader_core.models import Keyword, Symbol
from card_reader_parser.parsers.regions.bottom_region_parser import BottomRegionParser
from card_reader_parser.parsers.symbol_detector import DetectedSymbol, DetectionBBox


class StubOcrRunner:
    def run(self, _image: Image.Image) -> dict[str, object]:
        return {
            "text": ": target creature and gain devotion.",
            "confidence": 0.91,
            "lines": [{"text": ": target creature and gain devotion.", "confidence": 0.91}],
        }


class StubSymbolDetector:
    def __init__(self, detections: list[DetectedSymbol]) -> None:
        self._detections = detections
        self.last_expected_symbol_types: set[str] | None = None

    def detect(
        self,
        *,
        image: Image.Image,
        symbols: list[Symbol],
        expected_symbol_types: set[str] | None = None,
    ) -> list[DetectedSymbol]:
        _ = image
        _ = symbols
        self.last_expected_symbol_types = expected_symbol_types
        return self._detections


class StubMetadataExtractor:
    def extract_ids(self, text: str, known_keywords: list[Keyword]) -> list[str]:
        _ = text
        _ = known_keywords
        return ["keyword-1"]


def test_bottom_region_parser_detects_mana_devotion_and_generic_symbols_in_rules_text() -> None:
    detections = [
        DetectedSymbol(
            symbol_id="mana-1",
            key="arcane-mana",
            symbol_type="mana",
            confidence=0.97,
            bbox=DetectionBBox(x=10, y=5, w=12, h=12),
            detector_type="template",
            match_metadata={},
        ),
        DetectedSymbol(
            symbol_id="devotion-1",
            key="grimmothy-devotion",
            symbol_type="devotion",
            confidence=0.95,
            bbox=DetectionBBox(x=30, y=5, w=12, h=12),
            detector_type="template",
            match_metadata={},
        ),
        DetectedSymbol(
            symbol_id="misc-1",
            key="exhaust",
            symbol_type="generic",
            confidence=0.93,
            bbox=DetectionBBox(x=50, y=5, w=12, h=12),
            detector_type="template",
            match_metadata={},
        ),
    ]
    symbol_detector = StubSymbolDetector(detections)
    parser = BottomRegionParser(StubOcrRunner(), symbol_detector, StubMetadataExtractor())
    image = Image.new("RGB", (120, 40), "white")

    result = parser.parse(
        region_name="rules_text",
        image=image,
        region_spec={},
        symbols=[
            Symbol(id="mana-1", key="arcane-mana", label="Arcane Mana", symbol_type="mana"),
            Symbol(
                id="devotion-1",
                key="grimmothy-devotion",
                label="Grimmothy Devotion",
                symbol_type="devotion",
            ),
            Symbol(
                id="misc-1",
                key="exhaust",
                label="Exhaust",
                symbol_type="generic",
                text_token="{EXHAUST}",
                text_enrichment_json={"pattern_anchors": [{"match": ": ", "position": "before"}]},
            ),
            Symbol(id="affinity-1", key="affinity-sola", label="Affinity Sola", symbol_type="affinity"),
        ],
        known_keywords=[Keyword(id="keyword-1", key="exhaust", label="Exhaust")],
    )

    assert symbol_detector.last_expected_symbol_types == {"mana", "devotion", "generic"}
    assert result.normalized_fields == {
        "rules_text_raw": ": target creature and gain devotion.",
        "rules_text_enriched": "[[symbol:exhaust]]: target creature and gain devotion.",
        "rules_text": "{EXHAUST}: target creature and gain devotion.",
    }
    assert result.extracted_keyword_ids == ["keyword-1"]
    assert [row.symbol_id for row in result.detected_symbols] == ["mana-1", "devotion-1", "misc-1"]

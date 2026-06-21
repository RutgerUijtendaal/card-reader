from __future__ import annotations

from typing import Any

from PIL import Image

from card_reader_core.models import Symbol
from card_reader_parser.parsers.regions.name_mana_cost_parser import NameManaCostParser
from card_reader_parser.parsers.symbol_detector import DetectedSymbol, DetectionBBox


class StubOcrRunner:
    def __init__(self, text: str) -> None:
        self._text = text

    def run(self, _image: Image.Image, config: dict[str, object] | None = None) -> dict[str, object]:
        _ = config
        return {
            "text": self._text,
            "confidence": 0.9,
            "lines": [{"text": self._text, "confidence": 0.9}],
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


def test_name_mana_cost_parser_ignores_ocr_digits_when_symbols_are_detected() -> None:
    result = _parse(
        text="Draught of Memories 100",
        detections=[
            _detection("colorless-mana-1", x=90),
            _detection("occult-mana", x=120),
            _detection("occult-mana", x=150),
        ],
    )

    assert result.normalized_fields["name"] == "Draught of Memories"
    assert result.normalized_fields["mana_cost"] == "3"
    assert result.normalized_fields["mana_total"] == "3"
    assert result.normalized_fields["mana_symbols"] == "colorless-mana-1 occult-mana occult-mana"


def test_name_mana_cost_parser_counts_repeated_numeric_symbols() -> None:
    result = _parse(
        text="Twin Stone",
        detections=[
            _detection("colorless-mana-1", x=90),
            _detection("colorless-mana-1", x=120),
        ],
    )

    assert result.normalized_fields["mana_cost"] == "2"
    assert result.normalized_fields["mana_total"] == "2"
    assert result.normalized_fields["mana_symbols"] == "colorless-mana-1 colorless-mana-1"


def test_name_mana_cost_parser_uses_ocr_for_standalone_x_only() -> None:
    result = _parse(
        text="Unbound Memory X",
        detections=[
            _detection("occult-mana", x=90),
            _detection("occult-mana", x=120),
        ],
    )

    assert result.normalized_fields["name"] == "Unbound Memory X"
    assert result.normalized_fields["mana_cost"] == "X+2"
    assert result.normalized_fields["mana_total"] == "2"
    assert result.normalized_fields["mana_symbols"] == "occult-mana occult-mana x"


def test_name_mana_cost_parser_does_not_use_ocr_digits_without_symbols() -> None:
    result = _parse(text="False Cost 100", detections=[])

    assert result.normalized_fields["name"] == "False Cost 100"
    assert result.normalized_fields["mana_cost"] == "0"
    assert result.normalized_fields["mana_total"] == "0"
    assert result.normalized_fields["mana_symbols"] == ""


def test_name_mana_cost_parser_keeps_x_without_detected_symbols() -> None:
    result = _parse(text="Variable Spell X", detections=[])

    assert result.normalized_fields["name"] == "Variable Spell X"
    assert result.normalized_fields["mana_cost"] == "X"
    assert result.normalized_fields["mana_total"] == "0"
    assert result.normalized_fields["mana_symbols"] == "x"


def _parse(*, text: str, detections: list[DetectedSymbol]) -> Any:
    parser = NameManaCostParser(StubOcrRunner(text), StubSymbolDetector(detections))
    return parser.parse(
        region_name="top_bar",
        image=Image.new("RGB", (200, 40), "white"),
        image_stem="fallback-name",
        region_spec={},
        symbols=[
            _symbol("colorless-mana-1"),
            _symbol("occult-mana"),
        ],
    )


def _symbol(key: str) -> Symbol:
    return Symbol(
        id=key,
        key=key,
        label=key.replace("-", " ").title(),
        symbol_type="mana",
        detector_type="template",
        enabled=True,
    )


def _detection(key: str, *, x: int) -> DetectedSymbol:
    return DetectedSymbol(
        symbol_id=key,
        key=key,
        symbol_type="mana",
        confidence=0.95,
        bbox=DetectionBBox(x=x, y=5, w=12, h=12),
        detector_type="template",
        match_metadata={},
    )

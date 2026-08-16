from __future__ import annotations

from typing import Any

import pytest

from PIL import Image

from card_reader_core.models import (
    EVIL_CARD_POOL,
    NEUTRAL_CARD_POOL,
    PLAYER_CARD_POOL,
    CardPool,
    Symbol,
)
from card_reader_parser.parsers.regions.name_mana_cost_parser import NameManaCostParser
from card_reader_parser.parsers.symbol_detector import DetectedSymbol, DetectionBBox

MANA_BADGE_OCR_CONFIG = {
    "mana_badge_ocr": {
        "cut_region": {
            "unit": "relative",
            "x": 0.86,
            "y": 0.0,
            "w": 0.14,
            "h": 1.0,
        },
        "scales": [3, 2],
    }
}


class StubOcrRunner:
    def __init__(
        self,
        text: str | list[str],
        *,
        lines: list[str] | None = None,
        confidences: list[float] | None = None,
    ) -> None:
        self._texts = text if isinstance(text, list) else [text]
        self._lines = lines or [self._texts[0]]
        self._confidences = confidences or [0.9]
        self.calls: list[tuple[int, int]] = []

    def run(self, image: Image.Image, config: dict[str, object] | None = None) -> dict[str, object]:
        _ = config
        self.calls.append(image.size)
        call_index = len(self.calls) - 1
        text = self._texts[min(call_index, len(self._texts) - 1)]
        confidence = self._confidences[min(call_index, len(self._confidences) - 1)]
        lines = self._lines if len(self.calls) == 1 else [text]
        return {
            "text": text,
            "confidence": confidence,
            "lines": [{"text": line, "confidence": confidence} for line in lines],
        }


class StubSymbolDetector:
    def __init__(self, detections: list[DetectedSymbol]) -> None:
        self._detections = detections
        self.last_expected_symbol_types: set[str] | None = None
        self.call_count = 0

    def detect(
        self,
        *,
        image: Image.Image,
        symbols: list[Symbol],
        expected_symbol_types: set[str] | None = None,
    ) -> list[DetectedSymbol]:
        _ = image
        _ = symbols
        self.call_count += 1
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


@pytest.mark.parametrize(
    ("text", "expected_name", "expected_cost"),
    [
        ("Devourer 4", "Devourer", "4"),
        ("Ancient Devourer 12", "Ancient Devourer", "12"),
        ("Ancient Devourer 004", "Ancient Devourer", "4"),
    ],
)
def test_evil_name_mana_cost_parser_uses_trailing_ocr_integer(
    text: str,
    expected_name: str,
    expected_cost: str,
) -> None:
    result = _parse(
        text=text,
        detections=[_detection("occult-mana", x=120)],
        card_pool=EVIL_CARD_POOL,
        expected_detector_calls=0,
    )

    assert result.normalized_fields["name"] == expected_name
    assert result.normalized_fields["mana_cost"] == expected_cost
    assert result.normalized_fields["mana_total"] == expected_cost
    assert result.normalized_fields["mana_symbols"] == ""
    assert result.detected_symbols == []


def test_evil_name_mana_cost_parser_combines_split_ocr_lines() -> None:
    result = _parse(
        text="Devourer\n4",
        lines=["Devourer", "4"],
        detections=[],
        card_pool=EVIL_CARD_POOL,
        expected_detector_calls=0,
    )

    assert result.normalized_fields["name"] == "Devourer"
    assert result.normalized_fields["mana_cost"] == "4"
    assert result.normalized_fields["mana_total"] == "4"


def test_evil_name_mana_cost_parser_leaves_missing_cost_empty() -> None:
    result, ocr_runner = _parse_with_runner(
        text="Devourer",
        detections=[],
        card_pool=EVIL_CARD_POOL,
        expected_detector_calls=0,
    )

    assert result.normalized_fields["name"] == "Devourer"
    assert result.normalized_fields["mana_cost"] == ""
    assert result.normalized_fields["mana_total"] == ""
    assert result.normalized_fields["mana_symbols"] == ""
    assert ocr_runner.calls == [(200, 40)]


@pytest.mark.parametrize(
    ("badge_text", "expected_cost", "expected_total", "expected_symbols"),
    [
        ("X", "X", "0", "x"),
        ("1", "1", "1", ""),
    ],
)
def test_evil_name_mana_cost_parser_reads_isolated_badge_with_scaled_fallback(
    badge_text: str,
    expected_cost: str,
    expected_total: str,
    expected_symbols: str,
) -> None:
    result, ocr_runner = _parse_with_runner(
        text=["Counter Rune" if badge_text == "X" else "Amulet of Order", badge_text],
        detections=[],
        card_pool=EVIL_CARD_POOL,
        expected_detector_calls=0,
        region_spec=MANA_BADGE_OCR_CONFIG,
        confidences=[0.4, 0.8],
    )

    assert result.normalized_fields["name"] == (
        "Counter Rune" if badge_text == "X" else "Amulet of Order"
    )
    assert result.normalized_fields["mana_cost"] == expected_cost
    assert result.normalized_fields["mana_total"] == expected_total
    assert result.normalized_fields["mana_symbols"] == expected_symbols
    assert ocr_runner.calls == [(200, 40), (84, 120)]
    assert result.text.endswith(f"\n{badge_text}")
    assert [line["text"] for line in result.lines] == [
        "Counter Rune" if badge_text == "X" else "Amulet of Order",
        badge_text,
    ]
    assert result.lines[-1]["ocr_source"] == "mana_badge"
    assert result.confidence == pytest.approx(0.6)


def test_evil_name_mana_cost_parser_does_not_treat_trailing_title_x_as_mana() -> None:
    result, ocr_runner = _parse_with_runner(
        text=["Project X", "", ""],
        detections=[],
        card_pool=EVIL_CARD_POOL,
        expected_detector_calls=0,
        region_spec=MANA_BADGE_OCR_CONFIG,
    )

    assert result.normalized_fields["name"] == "Project X"
    assert result.normalized_fields["mana_cost"] == ""
    assert result.normalized_fields["mana_total"] == ""
    assert result.normalized_fields["mana_symbols"] == ""
    assert ocr_runner.calls == [(200, 40), (84, 120), (56, 80)]


def test_neutral_name_mana_cost_parser_leaves_cost_fields_empty() -> None:
    result = _parse(
        text="Neutral Relic",
        detections=[_detection("occult-mana", x=120)],
        card_pool=NEUTRAL_CARD_POOL,
        expected_detector_calls=0,
    )

    assert result.normalized_fields["name"] == "Neutral Relic"
    assert result.normalized_fields["mana_cost"] == ""
    assert result.normalized_fields["mana_total"] == ""
    assert result.normalized_fields["mana_symbols"] == ""
    assert result.detected_symbols == []


def _parse(
    *,
    text: str | list[str],
    detections: list[DetectedSymbol],
    lines: list[str] | None = None,
    card_pool: CardPool = PLAYER_CARD_POOL,
    expected_detector_calls: int = 1,
    region_spec: dict[str, Any] | None = None,
    confidences: list[float] | None = None,
) -> Any:
    result, _ocr_runner = _parse_with_runner(
        text=text,
        detections=detections,
        lines=lines,
        card_pool=card_pool,
        expected_detector_calls=expected_detector_calls,
        region_spec=region_spec,
        confidences=confidences,
    )
    return result


def _parse_with_runner(
    *,
    text: str | list[str],
    detections: list[DetectedSymbol],
    lines: list[str] | None = None,
    card_pool: CardPool = PLAYER_CARD_POOL,
    expected_detector_calls: int = 1,
    region_spec: dict[str, Any] | None = None,
    confidences: list[float] | None = None,
) -> tuple[Any, StubOcrRunner]:
    detector = StubSymbolDetector(detections)
    ocr_runner = StubOcrRunner(text, lines=lines, confidences=confidences)
    parser = NameManaCostParser(ocr_runner, detector)
    result = parser.parse(
        region_name="top_bar",
        image=Image.new("RGB", (200, 40), "white"),
        image_stem="fallback-name",
        card_pool=card_pool,
        region_spec=region_spec or {},
        symbols=[
            _symbol("colorless-mana-1"),
            _symbol("occult-mana"),
        ],
    )
    assert detector.call_count == expected_detector_calls
    return result, ocr_runner


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

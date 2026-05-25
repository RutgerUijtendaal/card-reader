from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from card_reader_parser.parsers.ocr_runner import OcrRunner
from card_reader_parser.parsers.regions.stats_region_parser import StatsRegionParser

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "stats-region"


class StubOcrRunner:
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
        self.calls: list[tuple[int, int]] = []

    def run(self, image: Image.Image, config: dict[str, object] | None = None) -> dict[str, object]:
        _ = config
        self.calls.append(image.size)
        text = self._texts[len(self.calls) - 1] if len(self.calls) <= len(self._texts) else ""
        return {
            "text": text,
            "confidence": 0.9,
            "lines": [{"text": text, "confidence": 0.9}] if text else [],
        }


@pytest.mark.parametrize(
    ("fixture_name", "field_name", "expected_value"),
    [
        ("bottom-left-2.png", "attack", "2"),
        ("bottom-left-5.png", "attack", "5"),
        ("bottom-right-empty.png", "health", None),
    ],
)
def test_stats_region_parser_extracts_expected_value_from_fixture(
    fixture_name: str,
    field_name: str,
    expected_value: str | None,
) -> None:
    fixture_path = FIXTURES_DIR / fixture_name
    if not fixture_path.exists():
        pytest.skip(f"Missing stats fixture image: {fixture_path}")

    parser = StatsRegionParser(OcrRunner())

    with Image.open(fixture_path) as image:
        result = parser.parse(
            region_name="stats",
            field_name=field_name,
            image=image.copy(),
            region_spec={},
        )

    if expected_value is None:
        assert field_name not in result.normalized_fields
    else:
        assert result.normalized_fields.get(field_name) == expected_value


def test_stats_region_parser_tries_richer_preprocessing_until_number_found() -> None:
    parser = StatsRegionParser(StubOcrRunner(["", "", "0"]))
    image = Image.new("RGB", (20, 20), "white")

    result = parser.parse(
        region_name="stats",
        field_name="attack",
        image=image,
        region_spec={},
    )

    assert result.normalized_fields.get("attack") == "0"
    stub_runner = parser._ocr_runner
    assert isinstance(stub_runner, StubOcrRunner)
    assert stub_runner.calls == [(20, 20), (20, 20), (40, 40)]

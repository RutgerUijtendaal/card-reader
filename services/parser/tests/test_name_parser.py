from __future__ import annotations

from PIL import Image

from card_reader_parser.parsers.regions.name_parser import NameParser


class StubOcrRunner:
    def __init__(self, lines: list[dict[str, object]]) -> None:
        self._lines = lines
        self.calls: list[dict[str, object] | None] = []

    def run(
        self,
        _image: Image.Image,
        config: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.calls.append(config)
        return {"lines": self._lines}


def test_name_parser_extracts_only_name_and_preserves_numeric_suffix() -> None:
    ocr_runner = StubOcrRunner(
        [
            {"text": "Prototype 2 ★ reminder", "confidence": 0.8},
            {"text": "", "confidence": 1.0},
        ]
    )
    parser = NameParser(ocr_runner)

    result = parser.parse(
        region_name="name_bar",
        image=Image.new("RGB", (200, 40), "white"),
        image_stem="fallback-name",
        region_spec={"ocr_config": {"ocr_min_confidence": 0.55}},
    )

    assert result.normalized_fields == {"name": "Prototype 2"}
    assert result.detected_symbols == []
    assert result.text == "Prototype 2 ★ reminder"
    assert result.confidence == 0.9
    assert result.debug["ocr_line_count_raw"] == 2
    assert "candidate_symbol_count" not in result.debug
    assert "expected_symbol_types" not in result.debug
    assert len(ocr_runner.calls) == 1


def test_name_parser_falls_back_to_image_stem_for_empty_ocr() -> None:
    parser = NameParser(StubOcrRunner([]))

    result = parser.parse(
        region_name="name_bar",
        image=Image.new("RGB", (200, 40), "white"),
        image_stem="fallback-name",
        region_spec={},
    )

    assert result.normalized_fields == {"name": "fallback-name"}
    assert result.text == ""
    assert result.confidence == 0.0

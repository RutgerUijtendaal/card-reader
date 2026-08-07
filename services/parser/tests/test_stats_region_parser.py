from __future__ import annotations

from PIL import Image

from card_reader_parser.parsers.regions.stats_region_parser import StatsRegionParser


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

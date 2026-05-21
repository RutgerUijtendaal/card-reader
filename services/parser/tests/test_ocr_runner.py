from __future__ import annotations

from PIL import Image

from card_reader_parser.parsers.ocr_runner import OcrRunner
from card_reader_parser.parsers.region_config import build_ocr_engine_config


def test_ocr_runner_filters_lines_by_region_min_confidence() -> None:
    runner = OcrRunner()
    payload = {
        "res": {
            "rec_texts": ["Name", "Ignored"],
            "rec_scores": [0.91, 0.42],
            "rec_polys": [
                [[0, 0], [10, 0], [10, 10], [0, 10]],
                [[0, 20], [10, 20], [10, 30], [0, 30]],
            ],
        }
    }

    result = runner._finalize_from_json_payload(payload, min_confidence=0.5)

    assert result["text"] == "Name"
    assert result["confidence"] == 0.91
    assert [line["text"] for line in result["lines"]] == ["Name"]


def test_ocr_runner_merges_default_engine_config_with_region_overrides() -> None:
    merged = build_ocr_engine_config(
        {
            "SubModules": {
                "TextDetection": {
                    "limit_side_len": 768,
                },
                "TextRecognition": {
                    "score_thresh": 0.65,
                },
            },
            "ocr_min_confidence": 0.5,
        }
    )

    assert merged["pipeline_name"] == "OCR"
    assert merged["SubModules"]["TextDetection"]["limit_side_len"] == 768
    assert merged["SubModules"]["TextDetection"]["box_thresh"] == 0.6
    assert merged["SubModules"]["TextRecognition"]["score_thresh"] == 0.65
    assert "ocr_min_confidence" not in merged


def test_ocr_runner_run_passes_merged_config_to_engine(monkeypatch) -> None:
    class StubPrediction:
        def __init__(self) -> None:
            self.json = {
                "res": {
                    "rec_texts": ["Hello"],
                    "rec_scores": [0.83],
                    "rec_polys": [[[0, 0], [10, 0], [10, 10], [0, 10]]],
                }
            }

    class StubEngine:
        def predict(self, _image: object) -> list[StubPrediction]:
            return [StubPrediction()]

    runner = OcrRunner()
    captured: dict[str, object] = {}

    def fake_get_engine(config: dict[str, object]) -> StubEngine:
        captured["config"] = config
        return StubEngine()

    monkeypatch.setattr(runner, "_get_ocr_engine", fake_get_engine)

    result = runner.run(
        Image.new("RGB", (10, 10), "white"),
        config={
            "SubModules": {
                "TextDetection": {"limit_side_len": 640},
            },
            "ocr_min_confidence": 0.5,
        },
    )

    assert result["text"] == "Hello"
    config = captured["config"]
    assert isinstance(config, dict)
    assert config["SubModules"]["TextDetection"]["limit_side_len"] == 640
    assert config["SubModules"]["TextRecognition"]["score_thresh"] == 0.8

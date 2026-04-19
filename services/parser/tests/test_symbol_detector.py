from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from card_reader_core.models import Symbol
from card_reader_parser.parsers.symbol_detector import SymbolDetector


def _fixture_symbol_asset_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "symbols" / "arcane-mana.webp"


def test_template_symbol_detector_finds_symbol_in_its_own_image() -> None:
    asset_path = _fixture_symbol_asset_path()
    if not asset_path.exists():
        pytest.skip(f"Missing symbol fixture asset: {asset_path}")

    detector = SymbolDetector()
    symbol = Symbol(
        key="arcane-mana",
        label="Arcane Mana",
        symbol_type="mana",
        detector_type="template",
        detection_config_json=json.dumps(
            {
                "threshold": 0.8,
                "scales": [1.0],
                "max_candidates_per_asset": 20,
                "max_detections_per_symbol": 5,
                "nms_iou_threshold": 0.2,
            }
        ),
        reference_assets_json=json.dumps([str(asset_path)]),
        text_token="{AM}",
        enabled=True,
    )

    with Image.open(asset_path) as image:
        detections = detector.detect(
            image=image.copy(),
            symbols=[symbol],
            expected_symbol_types={"mana"},
        )

    assert len(detections) >= 1
    assert any(item.key == "arcane-mana" for item in detections)


def test_template_symbol_detector_returns_empty_when_no_match() -> None:
    asset_path = _fixture_symbol_asset_path()
    if not asset_path.exists():
        pytest.skip(f"Missing symbol fixture asset: {asset_path}")

    detector = SymbolDetector()
    symbol = Symbol(
        key="arcane-mana",
        label="Arcane Mana",
        symbol_type="mana",
        detector_type="template",
        detection_config_json=json.dumps({"threshold": 0.95, "scales": [1.0]}),
        reference_assets_json=json.dumps([str(asset_path)]),
        text_token="{AM}",
        enabled=True,
    )

    blank = Image.new("RGB", (96, 96), color=(255, 255, 255))
    detections = detector.detect(
        image=blank,
        symbols=[symbol],
        expected_symbol_types={"mana"},
    )

    assert detections == []

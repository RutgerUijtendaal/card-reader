from __future__ import annotations

from pathlib import Path

from PIL import Image

from card_reader_parser.parsers.region_cropper import RegionCropper


def test_crop_regions_uses_region_entries_and_cut_region(tmp_path: Path) -> None:
    image_path = tmp_path / "card.png"
    Image.new("RGB", (100, 200), "white").save(image_path)

    template = {
        "regions": [
            {
                "region_id": "top_bar",
                "parser_type": "name_mana_cost",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.1,
                    "y": 0.2,
                    "w": 0.5,
                    "h": 0.25,
                },
                "ocr_config": {},
            }
        ]
    }

    crops = RegionCropper().crop_regions(image_path=image_path, template=template)

    assert set(crops.keys()) == {"top_bar"}
    assert crops["top_bar"]["x"] == 10
    assert crops["top_bar"]["y"] == 40
    assert crops["top_bar"]["w"] == 50
    assert crops["top_bar"]["h"] == 50
    assert crops["top_bar"]["image"].size == (50, 50)

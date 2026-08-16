from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from card_reader_core.models import EVIL_CARD_POOL
from card_reader_core.services.templates import NAME_MANA_COST, TemplateService
from card_reader_parser.parsers.region_cropper import RegionCropper
from card_reader_parser.parsers.regions.name_mana_cost_parser import NameManaCostParser
from card_reader_parser.parsers.symbol_detector import SymbolDetector

if TYPE_CHECKING:
    from card_reader_parser.parsers.ocr_runner import OcrRunner

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "cards"


@pytest.mark.parametrize(
    ("fixture_name", "expected_name", "expected_cost", "expected_total", "expected_symbols"),
    [
        ("counter-rune.webp", "Counter Rune", "X", "0", "x"),
        ("amulet-of-order.webp", "Amulet of Order", "1", "1", ""),
    ],
)
def test_evil_name_mana_cost_parser_reads_isolated_badge_from_fixture(
    fixture_name: str,
    expected_name: str,
    expected_cost: str,
    expected_total: str,
    expected_symbols: str,
    integration_ocr_runner: OcrRunner,
) -> None:
    fixture_path = FIXTURES_DIR / fixture_name
    assert fixture_path.exists(), f"Missing card fixture image: {fixture_path}"

    template = TemplateService().get_template_definition("mtg-like-v1")
    region_spec = next(
        region
        for region in template["regions"]
        if region.get("parser_type") == NAME_MANA_COST
    )
    top_bar = RegionCropper().crop_regions(
        image_path=fixture_path,
        template=template,
    )[str(region_spec["region_id"])]["image"]
    result = NameManaCostParser(integration_ocr_runner, SymbolDetector()).parse(
        region_name=str(region_spec["region_id"]),
        image=top_bar,
        image_stem=fixture_path.stem,
        card_pool=EVIL_CARD_POOL,
        region_spec=region_spec,
        symbols=[],
    )

    assert result.normalized_fields["name"] == expected_name
    assert result.normalized_fields["mana_cost"] == expected_cost
    assert result.normalized_fields["mana_total"] == expected_total
    assert result.normalized_fields["mana_symbols"] == expected_symbols

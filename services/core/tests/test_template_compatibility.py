from __future__ import annotations

from typing import Any

import pytest

from card_reader_core.services.templates import TemplateService
from card_reader_core.services.templates.compatibility import (
    MTG_LIKE_V1_MANA_BADGE_OCR,
    apply_bundled_template_compatibility,
)


def test_bundled_mtg_like_template_receives_mana_badge_ocr_config() -> None:
    definition = {
        "id": "mtg-like-v1",
        "regions": [
            {
                "region_id": "top_bar",
                "parser_type": "name_mana_cost",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.04,
                    "y": 0.02,
                    "w": 0.92,
                    "h": 0.07,
                },
                "ocr_config": {},
            }
        ],
    }

    upgraded = apply_bundled_template_compatibility(
        key="mtg-like-v1",
        definition=definition,
    )

    assert upgraded["regions"][0]["mana_badge_ocr"] == MTG_LIKE_V1_MANA_BADGE_OCR
    assert "mana_badge_ocr" not in definition["regions"][0]


def test_bundled_template_compatibility_preserves_custom_layout() -> None:
    definition = {
        "id": "mtg-like-v1",
        "regions": [
            {
                "region_id": "top_bar",
                "parser_type": "name_mana_cost",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.1,
                    "y": 0.1,
                    "w": 0.8,
                    "h": 0.1,
                },
                "ocr_config": {},
            }
        ],
    }

    assert (
        apply_bundled_template_compatibility(
            key="mtg-like-v1",
            definition=definition,
        )
        == definition
    )


def test_template_validation_rejects_unsafe_mana_badge_scale() -> None:
    definition = {
        "id": "mtg-like-v1",
        "regions": [
            {
                "region_id": "top_bar",
                "parser_type": "name_mana_cost",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.04,
                    "y": 0.02,
                    "w": 0.92,
                    "h": 0.07,
                },
                "mana_badge_ocr": {
                    "cut_region": {
                        "unit": "relative",
                        "x": 0.86,
                        "y": 0.0,
                        "w": 0.14,
                        "h": 1.0,
                    },
                    "scales": [3000],
                },
                "ocr_config": {},
            }
        ],
    }

    with pytest.raises(ValueError, match="scales values must be integers from 1 to 4"):
        TemplateService()._validate_template_definition(definition)


def test_template_validation_bounds_mana_badge_attempt_count() -> None:
    definition = _template_definition_with_badge()
    definition["regions"][0]["mana_badge_ocr"]["scales"] = [1, 2, 3, 4, 1]

    with pytest.raises(ValueError, match="scales may contain at most 4 values"):
        TemplateService()._validate_template_definition(definition)


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("unit", "pixels", "unit must be relative or absolute"),
        ("x", "right", "x must be a finite number"),
        ("w", float("inf"), "w must be a finite number"),
        ("h", 0, "w and .*h must be greater than zero"),
    ],
)
def test_template_validation_rejects_invalid_mana_badge_bounds(
    field: str,
    value: object,
    expected_error: str,
) -> None:
    definition = _template_definition_with_badge()
    definition["regions"][0]["mana_badge_ocr"]["cut_region"][field] = value

    with pytest.raises(ValueError, match=expected_error):
        TemplateService()._validate_template_definition(definition)


def _template_definition_with_badge() -> dict[str, Any]:
    return {
        "id": "mtg-like-v1",
        "regions": [
            {
                "region_id": "top_bar",
                "parser_type": "name_mana_cost",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.04,
                    "y": 0.02,
                    "w": 0.92,
                    "h": 0.07,
                },
                "mana_badge_ocr": {
                    "cut_region": {
                        "unit": "relative",
                        "x": 0.86,
                        "y": 0.0,
                        "w": 0.14,
                        "h": 1.0,
                    },
                    "scales": [3, 2],
                },
                "ocr_config": {},
            }
        ],
    }

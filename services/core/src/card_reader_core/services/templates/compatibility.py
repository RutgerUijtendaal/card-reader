from __future__ import annotations

from copy import deepcopy
from typing import Any


MTG_LIKE_V1_KEY = "mtg-like-v1"
MTG_LIKE_V1_NAME_REGION_CUT = {
    "unit": "relative",
    "x": 0.04,
    "y": 0.02,
    "w": 0.92,
    "h": 0.07,
}
MTG_LIKE_V1_MANA_BADGE_OCR = {
    "cut_region": {
        "unit": "relative",
        "x": 0.86,
        "y": 0.0,
        "w": 0.14,
        "h": 1.0,
    },
    "scales": [3, 2],
}


def apply_bundled_template_compatibility(
    *,
    key: str,
    definition: dict[str, Any],
) -> dict[str, Any]:
    """Upgrade immutable bundled templates whose runtime support changed."""
    if key != MTG_LIKE_V1_KEY:
        return definition

    regions = definition.get("regions")
    if not isinstance(regions, list):
        return definition

    upgraded = deepcopy(definition)
    for region in upgraded["regions"]:
        if not isinstance(region, dict):
            continue
        if region.get("parser_type") != "name_mana_cost":
            continue
        if region.get("cut_region") != MTG_LIKE_V1_NAME_REGION_CUT:
            continue
        region.setdefault("mana_badge_ocr", deepcopy(MTG_LIKE_V1_MANA_BADGE_OCR))
        break
    return upgraded

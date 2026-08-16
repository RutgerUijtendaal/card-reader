from __future__ import annotations

from copy import deepcopy
from typing import Any

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


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


def add_mtg_like_mana_badge_ocr(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    Template = apps.get_model("card_reader_core", "Template")
    template = Template.objects.filter(key="mtg-like-v1").first()
    if template is None or not isinstance(template.definition_json, dict):
        return

    definition: dict[str, Any] = deepcopy(template.definition_json)
    regions = definition.get("regions")
    if not isinstance(regions, list):
        return

    for region in regions:
        if not isinstance(region, dict):
            continue
        if region.get("parser_type") != "name_mana_cost":
            continue
        if region.get("cut_region") != MTG_LIKE_V1_NAME_REGION_CUT:
            continue
        if "mana_badge_ocr" in region:
            return
        region["mana_badge_ocr"] = deepcopy(MTG_LIKE_V1_MANA_BADGE_OCR)
        template.definition_json = definition
        template.save(update_fields=["definition_json", "updated_at"])
        return


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0058_add_mana_card_role")]

    operations = [
        migrations.RunPython(
            add_mtg_like_mana_badge_ocr,
            migrations.RunPython.noop,
        )
    ]

from __future__ import annotations

import json
from typing import Any

from django.db import migrations, models


DEFAULT_FIELD_SOURCES = {
    "fields": {
        "name": "auto",
        "type_line": "auto",
        "mana_cost": "auto",
        "attack": "auto",
        "health": "auto",
        "rules_text": "auto",
    },
    "metadata": {
        "keywords": "auto",
        "tags": "auto",
        "types": "auto",
        "symbols": "auto",
    },
}


def backfill_card_version_edit_state(apps: Any, _schema_editor: Any) -> None:
    card_version_model = apps.get_model("card_reader_core", "CardVersion")
    card_version_keyword_model = apps.get_model("card_reader_core", "CardVersionKeyword")
    card_version_tag_model = apps.get_model("card_reader_core", "CardVersionTag")
    card_version_type_model = apps.get_model("card_reader_core", "CardVersionType")
    card_version_symbol_model = apps.get_model("card_reader_core", "CardVersionSymbol")

    for version in card_version_model.objects.all():
        snapshot = {
            "fields": {
                "name": version.name,
                "type_line": version.type_line,
                "mana_cost": version.mana_cost,
                "attack": version.attack,
                "health": version.health,
                "rules_text": version.rules_text,
            },
            "metadata": {
                "keyword_ids": list(
                    card_version_keyword_model.objects.filter(card_version_id=version.id)
                    .values_list("keyword_id", flat=True)
                ),
                "tag_ids": list(
                    card_version_tag_model.objects.filter(card_version_id=version.id)
                    .values_list("tag_id", flat=True)
                ),
                "type_ids": list(
                    card_version_type_model.objects.filter(card_version_id=version.id)
                    .values_list("type_id", flat=True)
                ),
                "symbol_ids": list(
                    card_version_symbol_model.objects.filter(card_version_id=version.id)
                    .values_list("symbol_id", flat=True)
                ),
            },
        }
        version.field_sources_json = json.dumps(DEFAULT_FIELD_SOURCES)
        version.parsed_snapshot_json = json.dumps(snapshot)
        version.save(update_fields=["field_sources_json", "parsed_snapshot_json"])


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0007_tag_type_identifiers")]

    operations = [
        migrations.AddField(
            model_name="cardversion",
            name="field_sources_json",
            field=models.TextField(default="{}"),
        ),
        migrations.AddField(
            model_name="cardversion",
            name="parsed_snapshot_json",
            field=models.TextField(default="{}"),
        ),
        migrations.RunPython(backfill_card_version_edit_state, migrations.RunPython.noop),
    ]

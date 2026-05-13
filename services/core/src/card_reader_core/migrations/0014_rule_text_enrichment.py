from __future__ import annotations

from typing import Any

from django.db import migrations, models


def backfill_rule_text_fields(apps: Any, _schema_editor: Any) -> None:
    CardVersion = apps.get_model("card_reader_core", "CardVersion")
    for version in CardVersion.objects.all().only("id", "rules_text"):
        version.rules_text_raw = version.rules_text
        version.rules_text_enriched = version.rules_text
        version.save(update_fields=["rules_text_raw", "rules_text_enriched"])


class Migration(migrations.Migration):
    dependencies = [
        ("card_reader_core", "0013_native_json_and_relations"),
    ]

    operations = [
        migrations.AddField(
            model_name="cardversion",
            name="rules_text_enriched",
            field=models.TextField(default=""),
        ),
        migrations.AddField(
            model_name="cardversion",
            name="rules_text_raw",
            field=models.TextField(default=""),
        ),
        migrations.AddField(
            model_name="symbol",
            name="text_enrichment_json",
            field=models.JSONField(default=dict),
        ),
        migrations.RunPython(backfill_rule_text_fields, migrations.RunPython.noop),
    ]

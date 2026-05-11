from __future__ import annotations

import json
from typing import Any

from django.db import migrations, models


def backfill_identifiers(apps: Any, _schema_editor: Any) -> None:
    for model_name in ("Tag", "Type"):
        model = apps.get_model("card_reader_core", model_name)
        for row in model.objects.all():
            label = " ".join((row.label or "").split()).strip()
            identifier = label.lower()
            row.identifiers_json = json.dumps([identifier] if identifier else [])
            row.save(update_fields=["identifiers_json"])


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0006_keyword_identifiers")]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="identifiers_json",
            field=models.TextField(default="[]"),
        ),
        migrations.AddField(
            model_name="type",
            name="identifiers_json",
            field=models.TextField(default="[]"),
        ),
        migrations.RunPython(backfill_identifiers, migrations.RunPython.noop),
    ]

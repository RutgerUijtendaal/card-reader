from __future__ import annotations

import json
from typing import Any

from django.db import migrations, models


def backfill_keyword_identifiers(apps: Any, _schema_editor: Any) -> None:
    keyword_model = apps.get_model("card_reader_core", "Keyword")
    for keyword in keyword_model.objects.all():
        label = " ".join((keyword.label or "").split()).strip()
        identifier = label.lower()
        keyword.identifiers_json = json.dumps([identifier] if identifier else [])
        keyword.save(update_fields=["identifiers_json"])


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0005_card_version_search")]

    operations = [
        migrations.AddField(
            model_name="keyword",
            name="identifiers_json",
            field=models.TextField(default="[]"),
        ),
        migrations.RunPython(backfill_keyword_identifiers, migrations.RunPython.noop),
    ]

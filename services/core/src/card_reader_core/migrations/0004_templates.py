from __future__ import annotations

import card_reader_core.models.base
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0003_catalog")]

    operations = [
        migrations.CreateModel(
            name="Template",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("key", models.TextField(db_index=True, default="", unique=True)),
                ("label", models.TextField(default="")),
                ("definition_json", models.TextField(default="{}")),
            ],
            options={"db_table": "template"},
        ),
    ]

from __future__ import annotations

import card_reader_core.models.base
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0001_cards")]

    operations = [
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("source_path", models.TextField()),
                ("template_id", models.TextField()),
                ("options_json", models.TextField(default="{}")),
                ("status", models.TextField(default="queued")),
                ("total_items", models.IntegerField(default=0)),
                ("processed_items", models.IntegerField(default=0)),
            ],
            options={"db_table": "import_job"},
        ),
        migrations.CreateModel(
            name="ImportJobItem",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("job_id", models.TextField(db_index=True)),
                ("source_file", models.TextField()),
                ("status", models.TextField(default="queued")),
                ("error_message", models.TextField(default=None, null=True)),
            ],
            options={"db_table": "import_job_item"},
        ),
    ]

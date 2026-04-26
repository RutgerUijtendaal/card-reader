from __future__ import annotations

import card_reader_core.models.base
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="Card",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("key", models.TextField(db_index=True, default="", unique=True)),
                ("label", models.TextField(default="")),
                ("latest_version_id", models.TextField(db_index=True, default=None, null=True)),
            ],
            options={"db_table": "card"},
        ),
        migrations.CreateModel(
            name="CardVersion",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("card_id", models.TextField(db_index=True)),
                ("version_number", models.IntegerField(db_index=True, default=1)),
                ("template_id", models.TextField(db_index=True)),
                ("image_hash", models.TextField(db_index=True)),
                ("name", models.TextField(default="")),
                ("type_line", models.TextField(default="")),
                ("mana_cost", models.TextField(default="")),
                ("mana_symbols_json", models.TextField(default="[]")),
                ("attack", models.IntegerField(default=None, null=True)),
                ("health", models.IntegerField(default=None, null=True)),
                ("rules_text", models.TextField(default="")),
                ("confidence", models.FloatField(default=0.0)),
                ("parse_result_id", models.TextField(db_index=True, default=None, null=True)),
                ("is_latest", models.BooleanField(db_index=True, default=True)),
                ("previous_version_id", models.TextField(db_index=True, default=None, null=True)),
            ],
            options={
                "db_table": "card_version",
                "indexes": [models.Index(fields=["card_id", "is_latest"], name="ix_card_version_card_latest")],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("card_id", "version_number"),
                        name="ux_card_version_card_version",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CardVersionImage",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("card_version_id", models.TextField(db_index=True)),
                ("source_file", models.TextField()),
                ("stored_path", models.TextField()),
                ("width", models.IntegerField(default=0)),
                ("height", models.IntegerField(default=0)),
                ("checksum", models.TextField(db_index=True)),
            ],
            options={"db_table": "card_version_image"},
        ),
        migrations.CreateModel(
            name="ParseResult",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("card_version_id", models.TextField(db_index=True)),
                ("raw_ocr_json", models.TextField()),
                ("normalized_fields_json", models.TextField()),
                ("confidence_json", models.TextField()),
            ],
            options={"db_table": "parse_result"},
        ),
    ]

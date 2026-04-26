from __future__ import annotations

import card_reader_core.models.base
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0002_imports")]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("key", models.TextField(db_index=True, default="", unique=True)),
                ("label", models.TextField(default="")),
            ],
            options={"db_table": "tag"},
        ),
        migrations.CreateModel(
            name="Symbol",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("key", models.TextField(db_index=True, default="", unique=True)),
                ("label", models.TextField(default="")),
                ("symbol_type", models.TextField(db_index=True, default="generic")),
                ("detector_type", models.TextField(db_index=True, default="template")),
                ("detection_config_json", models.TextField(default="{}")),
                ("reference_assets_json", models.TextField(default="[]")),
                ("text_token", models.TextField(default="")),
                ("enabled", models.BooleanField(db_index=True, default=True)),
            ],
            options={"db_table": "symbol"},
        ),
        migrations.CreateModel(
            name="Keyword",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("key", models.TextField(db_index=True, default="", unique=True)),
                ("label", models.TextField(default="")),
            ],
            options={"db_table": "keyword"},
        ),
        migrations.CreateModel(
            name="Type",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("key", models.TextField(db_index=True, default="", unique=True)),
                ("label", models.TextField(default="")),
            ],
            options={"db_table": "type"},
        ),
        migrations.CreateModel(
            name="CardVersionTag",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("card_version_id", models.TextField(db_index=True)),
                ("tag_id", models.TextField(db_index=True)),
            ],
            options={
                "db_table": "card_version_tag",
                "constraints": [models.UniqueConstraint(fields=("card_version_id", "tag_id"), name="ux_card_version_tag_pair")],
            },
        ),
        migrations.CreateModel(
            name="CardVersionSymbol",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("card_version_id", models.TextField(db_index=True)),
                ("symbol_id", models.TextField(db_index=True)),
            ],
            options={
                "db_table": "card_version_symbol",
                "constraints": [models.UniqueConstraint(fields=("card_version_id", "symbol_id"), name="ux_card_version_symbol_pair")],
            },
        ),
        migrations.CreateModel(
            name="CardVersionKeyword",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("card_version_id", models.TextField(db_index=True)),
                ("keyword_id", models.TextField(db_index=True)),
            ],
            options={
                "db_table": "card_version_keyword",
                "constraints": [models.UniqueConstraint(fields=("card_version_id", "keyword_id"), name="ux_card_version_keyword_pair")],
            },
        ),
        migrations.CreateModel(
            name="CardVersionType",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("card_version_id", models.TextField(db_index=True)),
                ("type_id", models.TextField(db_index=True)),
            ],
            options={
                "db_table": "card_version_type",
                "constraints": [models.UniqueConstraint(fields=("card_version_id", "type_id"), name="ux_card_version_type_pair")],
            },
        ),
    ]

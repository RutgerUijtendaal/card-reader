from __future__ import annotations

import card_reader_core.models.base
from typing import ClassVar

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [("card_reader_core", "0024_deck_visibility")]

    operations = [
        migrations.CreateModel(
            name="CardAlias",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("key", models.TextField(db_index=True, default="", unique=True)),
                ("label", models.TextField(default="")),
                (
                    "card",
                    models.ForeignKey(
                        db_column="card_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aliases",
                        to="card_reader_core.card",
                    ),
                ),
            ],
            options={"db_table": "card_alias"},
        ),
        migrations.CreateModel(
            name="CardMergeRedirect",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("old_card_id", models.TextField(db_index=True, unique=True)),
                (
                    "target_card",
                    models.ForeignKey(
                        db_column="target_card_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="merge_redirects",
                        to="card_reader_core.card",
                    ),
                ),
            ],
            options={"db_table": "card_merge_redirect"},
        ),
    ]

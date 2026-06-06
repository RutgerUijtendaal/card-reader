from __future__ import annotations

from typing import ClassVar

import card_reader_core.models.base
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("card_reader_core", "0028_content_versions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CardVersionParseFlag",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("note", models.TextField(blank=True, default="")),
                (
                    "card_version",
                    models.ForeignKey(
                        db_column="card_version_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parse_flags",
                        to="card_reader_core.cardversion",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        db_column="submitted_by_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="card_version_parse_flags",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "card_version_parse_flag",
            },
        ),
        migrations.CreateModel(
            name="CardVersionParseFlagItem",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("property_key", models.TextField(db_index=True)),
                ("captured_current_value", models.TextField(blank=True, default="")),
                ("expected_value", models.TextField(blank=True, default="")),
                ("note", models.TextField(blank=True, default="")),
                ("status", models.TextField(db_index=True, default="open")),
                ("review_note", models.TextField(blank=True, default="")),
                ("reviewed_at", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "flag",
                    models.ForeignKey(
                        db_column="flag_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="card_reader_core.cardversionparseflag",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="reviewed_by_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_card_version_parse_flag_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "card_version_parse_flag_item",
            },
        ),
        migrations.AddIndex(
            model_name="cardversionparseflag",
            index=models.Index(fields=["card_version", "created_at"], name="ix_parse_flag_version_created"),
        ),
        migrations.AddIndex(
            model_name="cardversionparseflag",
            index=models.Index(fields=["submitted_by", "created_at"], name="ix_parse_flag_user_created"),
        ),
        migrations.AddIndex(
            model_name="cardversionparseflagitem",
            index=models.Index(fields=["status", "created_at"], name="ix_parse_flag_item_status_created"),
        ),
        migrations.AddIndex(
            model_name="cardversionparseflagitem",
            index=models.Index(fields=["property_key", "status"], name="ix_parse_flag_item_prop_status"),
        ),
    ]

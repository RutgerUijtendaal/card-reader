from __future__ import annotations

import card_reader_core.models.base
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0046_developer_data_builds")]

    operations = [
        migrations.CreateModel(
            name="TtsCardSheet",
            fields=[
                (
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("sequence", models.PositiveIntegerField(unique=True)),
                ("layout_version", models.PositiveSmallIntegerField(default=1)),
                ("next_slot_index", models.PositiveSmallIntegerField(default=0)),
                ("desired_revision", models.PositiveBigIntegerField(default=0)),
                ("desired_fingerprint", models.TextField(default="")),
                ("rendered_revision", models.PositiveBigIntegerField(default=0)),
                ("rendered_fingerprint", models.TextField(default="")),
                ("rendered_checksum", models.TextField(default="")),
                ("published_at", models.DateTimeField(default=None, null=True)),
                ("dirty_since", models.DateTimeField(default=None, null=True)),
                (
                    "render_not_before",
                    models.DateTimeField(db_index=True, default=None, null=True),
                ),
                (
                    "render_claimed_at",
                    models.DateTimeField(db_index=True, default=None, null=True),
                ),
                ("render_failure_count", models.PositiveIntegerField(default=0)),
                ("render_priority", models.PositiveSmallIntegerField(default=0)),
                ("last_render_error", models.TextField(default="")),
            ],
            options={
                "db_table": "tts_card_sheet",
                "ordering": ["sequence"],
            },
        ),
        migrations.CreateModel(
            name="TtsCardSheetSlot",
            fields=[
                (
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("slot_index", models.PositiveSmallIntegerField()),
                ("card_identity_id", models.TextField(unique=True)),
                ("image_checksum", models.TextField(default="")),
                ("image_stored_path", models.TextField(default="")),
                (
                    "card_version",
                    models.ForeignKey(
                        db_column="card_version_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="card_reader_core.cardversion",
                    ),
                ),
                (
                    "image",
                    models.ForeignKey(
                        db_column="image_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="card_reader_core.cardversionimage",
                    ),
                ),
                (
                    "resolved_card",
                    models.ForeignKey(
                        db_column="resolved_card_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="card_reader_core.card",
                    ),
                ),
                (
                    "sheet",
                    models.ForeignKey(
                        db_column="sheet_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="slots",
                        to="card_reader_core.ttscardsheet",
                    ),
                ),
            ],
            options={
                "db_table": "tts_card_sheet_slot",
                "ordering": ["sheet__sequence", "slot_index"],
            },
        ),
        migrations.AddIndex(
            model_name="ttscardsheet",
            index=models.Index(
                fields=["-render_priority", "render_not_before", "render_claimed_at", "sequence"],
                name="ix_tts_sheet_render_queue",
            ),
        ),
        migrations.AddConstraint(
            model_name="ttscardsheet",
            constraint=models.CheckConstraint(
                condition=models.Q(("next_slot_index__lte", 70)),
                name="ck_tts_sheet_next_slot_capacity",
            ),
        ),
        migrations.AddConstraint(
            model_name="ttscardsheet",
            constraint=models.CheckConstraint(
                condition=models.Q(("rendered_revision__lte", models.F("desired_revision"))),
                name="ck_tts_sheet_rendered_revision",
            ),
        ),
        migrations.AddConstraint(
            model_name="ttscardsheetslot",
            constraint=models.UniqueConstraint(
                fields=("sheet", "slot_index"),
                name="ux_tts_sheet_slot_position",
            ),
        ),
        migrations.AddConstraint(
            model_name="ttscardsheetslot",
            constraint=models.CheckConstraint(
                condition=models.Q(("slot_index__lt", 70)),
                name="ck_tts_sheet_slot_capacity",
            ),
        ),
    ]

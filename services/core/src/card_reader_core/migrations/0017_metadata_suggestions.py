from __future__ import annotations

from django.db import migrations, models

import card_reader_core.models.base


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0016_card_version_mana_value")]

    operations = [
        migrations.CreateModel(
            name="MetadataSuggestion",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("kind", models.TextField(db_index=True, default="")),
                ("normalized_value", models.TextField(db_index=True, default="")),
                ("display_value", models.TextField(default="")),
                ("status", models.TextField(db_index=True, default="pending")),
                (
                    "accepted_tag",
                    models.ForeignKey(
                        blank=True,
                        db_column="accepted_tag_id",
                        default=None,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="accepted_metadata_suggestions",
                        to="card_reader_core.tag",
                    ),
                ),
                (
                    "accepted_type",
                    models.ForeignKey(
                        blank=True,
                        db_column="accepted_type_id",
                        default=None,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="accepted_metadata_suggestions",
                        to="card_reader_core.type",
                    ),
                ),
            ],
            options={
                "db_table": "metadata_suggestion",
            },
        ),
        migrations.CreateModel(
            name="CardVersionMetadataSuggestion",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("source_text", models.TextField(default="")),
                ("normalized_source_text", models.TextField(default="")),
                (
                    "card_version",
                    models.ForeignKey(
                        db_column="card_version_id",
                        on_delete=models.deletion.CASCADE,
                        related_name="card_version_metadata_suggestions",
                        to="card_reader_core.cardversion",
                    ),
                ),
                (
                    "parse_result",
                    models.ForeignKey(
                        blank=True,
                        db_column="parse_result_id",
                        default=None,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="+",
                        to="card_reader_core.parseresult",
                    ),
                ),
                (
                    "suggestion",
                    models.ForeignKey(
                        db_column="suggestion_id",
                        on_delete=models.deletion.CASCADE,
                        related_name="card_version_metadata_suggestions",
                        to="card_reader_core.metadatasuggestion",
                    ),
                ),
            ],
            options={
                "db_table": "card_version_metadata_suggestion",
            },
        ),
        migrations.AddConstraint(
            model_name="metadatasuggestion",
            constraint=models.UniqueConstraint(
                fields=("kind", "normalized_value"),
                name="ux_metadata_suggestion_kind_value",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardversionmetadatasuggestion",
            constraint=models.UniqueConstraint(
                fields=("card_version", "suggestion"),
                name="ux_card_version_metadata_suggestion_pair",
            ),
        ),
    ]

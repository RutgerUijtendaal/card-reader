from django.db import migrations, models

import card_reader_core.models.base


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0021_import_job_item_reparse_targets")]

    operations = [
        migrations.CreateModel(
            name="DeckSideboard",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("name", models.TextField(default="")),
                (
                    "deck",
                    models.ForeignKey(
                        db_column="deck_id",
                        on_delete=models.deletion.CASCADE,
                        related_name="sideboards",
                        to="card_reader_core.deck",
                    ),
                ),
            ],
            options={
                "db_table": "deck_sideboard",
                "indexes": [models.Index(fields=["deck", "created_at"], name="ix_deck_sideboard_deck_created")],
            },
        ),
        migrations.CreateModel(
            name="DeckSideboardEntry",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("quantity", models.IntegerField(default=1)),
                (
                    "card",
                    models.ForeignKey(
                        db_column="card_id",
                        on_delete=models.deletion.CASCADE,
                        related_name="deck_sideboard_entries",
                        to="card_reader_core.card",
                    ),
                ),
                (
                    "sideboard",
                    models.ForeignKey(
                        db_column="sideboard_id",
                        on_delete=models.deletion.CASCADE,
                        related_name="entries",
                        to="card_reader_core.decksideboard",
                    ),
                ),
            ],
            options={
                "db_table": "deck_sideboard_entry",
                "indexes": [models.Index(fields=["sideboard", "created_at"], name="ix_deck_sideboard_entry_created")],
            },
        ),
    ]

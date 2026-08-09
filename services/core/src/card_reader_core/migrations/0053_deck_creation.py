from __future__ import annotations

from typing import Any

import card_reader_core.models.base
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_deck_creations(apps: Any, _schema_editor: Any) -> None:
    Deck = apps.get_model("card_reader_core", "Deck")
    DeckCreation = apps.get_model("card_reader_core", "DeckCreation")
    creations = [
        DeckCreation(
            owner_id=deck.owner_id,
            client_creation_id=deck.client_creation_id,
            deck_id=deck.id,
        )
        for deck in Deck.objects.exclude(client_creation_id=None).iterator()
    ]
    DeckCreation.objects.bulk_create(creations, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("card_reader_core", "0052_deck_client_creation_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeckCreation",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                (
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("client_creation_id", models.UUIDField()),
                (
                    "deck",
                    models.OneToOneField(
                        blank=True,
                        db_column="deck_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creation_record",
                        to="card_reader_core.deck",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        db_column="owner_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deck_creations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "deck_creation",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("owner", "client_creation_id"),
                        name="ux_deck_creation_owner_key",
                    )
                ],
            },
        ),
        migrations.RunPython(backfill_deck_creations, migrations.RunPython.noop),
    ]

from __future__ import annotations

import card_reader_core.models.base
from typing import Any

from django.conf import settings
from django.db import migrations, models


def _backfill_card_is_hero(apps: Any, _schema_editor: Any) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    Type = apps.get_model("card_reader_core", "Type")
    CardVersionType = apps.get_model("card_reader_core", "CardVersionType")

    hero_type = Type.objects.filter(key="hero").first()
    if hero_type is None:
        return

    hero_card_ids = (
        CardVersionType.objects.filter(
            type_id=hero_type.id,
            card_version__is_latest=True,
        )
        .values_list("card_version__card_id", flat=True)
        .distinct()
    )
    Card.objects.filter(id__in=hero_card_ids).update(is_hero=True)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("card_reader_core", "0019_card_version_template_uuid_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="card",
            name="is_hero",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.CreateModel(
            name="Deck",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("name", models.TextField(default="")),
                ("description", models.TextField(blank=True, default=None, null=True)),
                ("is_public", models.BooleanField(db_index=True, default=False)),
                (
                    "hero_card",
                    models.ForeignKey(
                        db_column="hero_card_id",
                        on_delete=models.PROTECT,
                        related_name="hero_decks",
                        to="card_reader_core.card",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        db_column="owner_id",
                        on_delete=models.CASCADE,
                        related_name="decks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "deck",
                "indexes": [models.Index(fields=["owner", "updated_at"], name="ix_deck_owner_updated")],
            },
        ),
        migrations.CreateModel(
            name="DeckEntry",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("quantity", models.IntegerField(default=1)),
                (
                    "card",
                    models.ForeignKey(
                        db_column="card_id",
                        on_delete=models.CASCADE,
                        related_name="deck_entries",
                        to="card_reader_core.card",
                    ),
                ),
                (
                    "deck",
                    models.ForeignKey(
                        db_column="deck_id",
                        on_delete=models.CASCADE,
                        related_name="entries",
                        to="card_reader_core.deck",
                    ),
                ),
            ],
            options={
                "db_table": "deck_entry",
                "indexes": [models.Index(fields=["deck", "created_at"], name="ix_deck_entry_deck_created")],
                "constraints": [
                    models.UniqueConstraint(fields=("deck", "card"), name="ux_deck_entry_deck_card"),
                ],
            },
        ),
        migrations.RunPython(_backfill_card_is_hero, reverse_code=migrations.RunPython.noop),
    ]

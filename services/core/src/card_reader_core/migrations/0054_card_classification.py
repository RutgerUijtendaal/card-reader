from __future__ import annotations

from typing import Any

import card_reader_core.models.base
from django.db import migrations, models
import django.db.models.deletion


HERO_CARD_ROLE = "hero"


def forwards(apps: Any, _schema_editor: Any) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card_id=card_id, role=HERO_CARD_ROLE)
            for card_id in Card.objects.filter(is_hero=True).values_list("id", flat=True).iterator()
        ],
        ignore_conflicts=True,
    )


def backwards(apps: Any, _schema_editor: Any) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    hero_card_ids = CardRoleAssignment.objects.filter(role=HERO_CARD_ROLE).values_list("card_id", flat=True)
    Card.objects.filter(id__in=hero_card_ids).update(is_hero=True)


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0053_deck_creation")]

    operations = [
        migrations.AddField(
            model_name="card",
            name="card_pool",
            field=models.CharField(
                choices=[("player", "Player"), ("game_master", "Game Master")],
                db_index=True,
                default="player",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="CardRoleAssignment",
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
                (
                    "role",
                    models.CharField(
                        choices=[("hero", "Hero"), ("boon", "Boon"), ("event", "Event")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                (
                    "card",
                    models.ForeignKey(
                        db_column="card_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to="card_reader_core.card",
                    ),
                ),
            ],
            options={
                "db_table": "card_role_assignment",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("card", "role"),
                        name="uq_card_role_assignment_card_role",
                    )
                ],
            },
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(model_name="card", name="is_hero"),
    ]

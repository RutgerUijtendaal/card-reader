from __future__ import annotations

from typing import Any

from django.db import migrations, models

import card_reader_core.models.base


FINAL_CARD_POOLS = ("player", "evil", "neutral")


def seed_identity_pool_locks(apps: Any, _schema_editor: Any) -> None:
    CardIdentityPoolLock = apps.get_model("card_reader_core", "CardIdentityPoolLock")
    CardIdentityPoolLock.objects.bulk_create(
        [CardIdentityPoolLock(card_pool=card_pool) for card_pool in FINAL_CARD_POOLS]
    )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0058_pool_scoped_card_identity")]

    operations = [
        migrations.CreateModel(
            name="CardIdentityPoolLock",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(default=card_reader_core.models.base.now_utc),
                ),
                (
                    "updated_at",
                    models.DateTimeField(default=card_reader_core.models.base.now_utc),
                ),
                (
                    "card_pool",
                    models.CharField(
                        choices=[("player", "Player"), ("evil", "Evil"), ("neutral", "Neutral")],
                        max_length=16,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("revision", models.PositiveBigIntegerField(default=0)),
            ],
            options={"db_table": "card_identity_pool_lock"},
        ),
        migrations.RunPython(seed_identity_pool_locks, migrations.RunPython.noop),
    ]

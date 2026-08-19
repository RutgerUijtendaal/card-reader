from typing import Any

import card_reader_core.models.base
import django.db.models.deletion
from django.db import migrations, models


CARD_POOLS = ("player", "evil", "neutral")


def adopt_current_card_back(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    card_back_model = apps.get_model("card_reader_core", "CardBack")
    pool_default_model = apps.get_model("card_reader_core", "CardBackPoolDefault")
    current = card_back_model.objects.filter(is_current=True).order_by(
        "-updated_at", "-created_at", "-id"
    ).first()
    if current is None:
        return
    pool_default_model.objects.bulk_create(
        [
            pool_default_model(card_pool=card_pool, card_back_id=current.id)
            for card_pool in CARD_POOLS
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0059_backfill_card_version_rules_text")]

    operations = [
        migrations.CreateModel(
            name="CardBackPoolDefault",
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
                (
                    "card_back",
                    models.ForeignKey(
                        db_column="card_back_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pool_defaults",
                        to="card_reader_core.cardback",
                    ),
                ),
            ],
            options={"db_table": "card_back_pool_default"},
        ),
        migrations.AddField(
            model_name="card",
            name="card_back_override",
            field=models.ForeignKey(
                blank=True,
                db_column="card_back_override_id",
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="card_overrides",
                to="card_reader_core.cardback",
            ),
        ),
        migrations.RunPython(adopt_current_card_back, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name="cardback", name="ux_card_back_single_current"),
        migrations.RemoveField(model_name="cardback", name="is_current"),
    ]

from __future__ import annotations

from typing import Any

from django.db import migrations, models
from django.db.models import Count


RESTRICTED_CARD_POOLS = ("evil", "neutral")
TEMPORARY_GAME_MASTER_POOL = "game_master"


def reject_temporary_pool_values(apps: Any, _schema_editor: Any) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")
    invalid_sources: list[str] = []
    if Card.objects.filter(card_pool=TEMPORARY_GAME_MASTER_POOL).exists():
        invalid_sources.append("cards")
    if ImportJob.objects.filter(card_pool=TEMPORARY_GAME_MASTER_POOL).exists():
        invalid_sources.append("import jobs")
    if ImportJobItem.objects.filter(target_card_pool_snapshot=TEMPORARY_GAME_MASTER_POOL).exists():
        invalid_sources.append("import item snapshots")
    if invalid_sources:
        raise RuntimeError(
            "Migration 0058 cannot replace the temporary 'game_master' card pool while persisted "
            f"values exist in: {', '.join(invalid_sources)}. Reclassify or remove that undeployed "
            "data before retrying; this migration intentionally does not guess Evil versus Neutral."
        )


def populate_alias_pools(apps: Any, _schema_editor: Any) -> None:
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    for alias in CardAlias.objects.select_related("card").iterator():
        alias.card_pool = alias.card.card_pool
        alias.save(update_fields=["card_pool"])


def guard_global_identity_restoration(apps: Any, _schema_editor: Any) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")

    restricted_sources: list[str] = []
    if Card.objects.filter(card_pool__in=RESTRICTED_CARD_POOLS).exists():
        restricted_sources.append("cards")
    if CardAlias.objects.filter(card_pool__in=RESTRICTED_CARD_POOLS).exists():
        restricted_sources.append("aliases")
    if ImportJob.objects.filter(card_pool__in=RESTRICTED_CARD_POOLS).exists():
        restricted_sources.append("import jobs")
    if ImportJobItem.objects.filter(target_card_pool_snapshot__in=RESTRICTED_CARD_POOLS).exists():
        restricted_sources.append("import item snapshots")
    if restricted_sources:
        raise RuntimeError(
            "Migration 0058 cannot be reversed while Evil or Neutral data exists in: "
            + ", ".join(restricted_sources)
            + "."
        )

    duplicate_card_keys = Card.objects.values("key").annotate(total=Count("id")).filter(total__gt=1)
    duplicate_alias_keys = CardAlias.objects.values("key").annotate(total=Count("id")).filter(total__gt=1)
    if duplicate_card_keys.exists() or duplicate_alias_keys.exists():
        raise RuntimeError(
            "Migration 0058 cannot be reversed while card or alias keys are duplicated across pools."
        )
    if Card.objects.filter(key__in=CardAlias.objects.values("key")).exists():
        raise RuntimeError(
            "Migration 0058 cannot be reversed while a primary card key also exists as an alias key."
        )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0057_location_card_role")]

    operations = [
        migrations.RunPython(reject_temporary_pool_values, migrations.RunPython.noop),
        migrations.AddField(
            model_name="cardalias",
            name="card_pool",
            field=models.CharField(
                blank=True,
                choices=[("player", "Player"), ("evil", "Evil"), ("neutral", "Neutral")],
                db_index=True,
                max_length=16,
                null=True,
            ),
        ),
        migrations.RunPython(populate_alias_pools, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="cardalias",
            name="card_pool",
            field=models.CharField(
                choices=[("player", "Player"), ("evil", "Evil"), ("neutral", "Neutral")],
                db_index=True,
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="key",
            field=models.TextField(db_index=True, default=""),
        ),
        migrations.AddConstraint(
            model_name="card",
            constraint=models.UniqueConstraint(fields=("card_pool", "key"), name="uq_card_pool_key"),
        ),
        migrations.AlterField(
            model_name="cardalias",
            name="key",
            field=models.TextField(db_index=True, default=""),
        ),
        migrations.AddConstraint(
            model_name="cardalias",
            constraint=models.UniqueConstraint(
                fields=("card_pool", "key"),
                name="uq_card_alias_pool_key",
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="card_pool",
            field=models.CharField(
                choices=[("player", "Player"), ("evil", "Evil"), ("neutral", "Neutral")],
                db_index=True,
                default="player",
                max_length=16,
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, guard_global_identity_restoration),
    ]

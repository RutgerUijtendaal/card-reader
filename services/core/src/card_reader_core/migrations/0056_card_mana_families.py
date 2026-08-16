from __future__ import annotations

from itertools import combinations
from typing import Any
from uuid import UUID, uuid5

from django.db import migrations, models
import django.db.models.deletion
import card_reader_core.models.base


FAMILIES = (
    ("arcane", "Arcane", "arcane-mana", ("arcane-affinity",)),
    ("dark", "Dark", "dark-mana", ("dark-affinity",)),
    ("divine", "Divine", "divine-mana", ("divine-affinity",)),
    ("martial", "Martial", "martial-mana", ("martial-affinity",)),
    ("occult", "Occult", "occult-mana", ("occult-affinity",)),
    ("primal", "Primal", "primal-mana", ("primal-affinity", "primla-affinity")),
)
FAMILY_BY_SYMBOL = {
    symbol_key: family_key
    for family_key, _label, mana_key, affinity_keys in FAMILIES
    for symbol_key in (mana_key, *affinity_keys)
}
MULTI_RANKS = {
    combination: len(FAMILIES) + index
    for index, combination in enumerate(
        sorted(
            combination
            for size in range(2, len(FAMILIES) + 1)
            for combination in combinations(range(len(FAMILIES)), size)
        )
    )
}
NO_FAMILY_SORT_KEY = len(FAMILIES) + len(MULTI_RANKS)
RULE_NAMESPACE = UUID("b26ccbd1-7014-46fc-874d-416f358be4c0")


def backfill_player_mana_families(apps, _schema_editor) -> None:  # type: ignore[no-untyped-def]
    Card = apps.get_model("card_reader_core", "Card")
    Assignment = apps.get_model("card_reader_core", "CardManaFamilyAssignment")
    VersionSymbol = apps.get_model("card_reader_core", "CardVersionSymbol")

    rows_by_card: dict[str, set[str]] = {}
    links = VersionSymbol.objects.filter(
        card_version__card__card_pool="player",
        card_version__card__latest_version_id=models.F("card_version_id"),
        symbol__key__in=tuple(FAMILY_BY_SYMBOL),
    ).values_list("card_version__card_id", "symbol__key")
    for card_id, symbol_key in links.iterator():
        rows_by_card.setdefault(str(card_id), set()).add(FAMILY_BY_SYMBOL[str(symbol_key)])

    assignments: list[Any] = []
    updates = []
    family_rank = {family[0]: rank for rank, family in enumerate(FAMILIES)}
    for card in Card.objects.filter(card_pool="player").iterator():
        families = tuple(
            family[0]
            for family in FAMILIES
            if family[0] in rows_by_card.get(str(card.id), set())
        )
        assignments.extend(
            Assignment(card_id=card.id, mana_family=family) for family in families
        )
        if len(assignments) >= 500:
            Assignment.objects.bulk_create(
                assignments,
                batch_size=500,
                ignore_conflicts=True,
            )
            assignments = []
        ranks = tuple(family_rank[family] for family in families)
        if len(ranks) == 1:
            card.mana_family_sort_key = ranks[0]
        elif len(ranks) > 1:
            card.mana_family_sort_key = MULTI_RANKS[ranks]
        else:
            card.mana_family_sort_key = NO_FAMILY_SORT_KEY
        updates.append(card)
        if len(updates) >= 500:
            Card.objects.bulk_update(updates, ["mana_family_sort_key"], batch_size=500)
            updates = []
    if assignments:
        Assignment.objects.bulk_create(
            assignments,
            batch_size=500,
            ignore_conflicts=True,
        )
    if updates:
        Card.objects.bulk_update(updates, ["mana_family_sort_key"], batch_size=500)


def seed_available_symbol_rules(apps, _schema_editor) -> None:  # type: ignore[no-untyped-def]
    Symbol = apps.get_model("card_reader_core", "Symbol")
    Rule = apps.get_model("card_reader_core", "CardClassificationRule")
    symbols = {row.key: row for row in Symbol.objects.filter(key__in=tuple(FAMILY_BY_SYMBOL))}
    for family_key, _label, mana_key, affinity_keys in FAMILIES:
        for symbol_key in (mana_key, *affinity_keys):
            symbol = symbols.get(symbol_key)
            if symbol is None:
                continue
            identity = f"player:mana_family:{family_key}:symbol:{symbol_key}"
            Rule.objects.get_or_create(
                card_pool="player",
                target_kind="mana_family",
                target_key=family_key,
                source_kind="symbol",
                symbol_id=symbol.id,
                defaults={"id": str(uuid5(RULE_NAMESPACE, identity)), "enabled": True},
            )


def remove_symbol_rules_for_downgrade(apps, _schema_editor) -> None:  # type: ignore[no-untyped-def]
    Rule = apps.get_model("card_reader_core", "CardClassificationRule")
    Rule.objects.filter(source_kind="symbol").delete()


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0055_seed_classification_rules_and_full_height_template")]

    operations = [
        migrations.AddField(
            model_name="card",
            name="mana_family_sort_key",
            field=models.PositiveSmallIntegerField(default=63, db_index=True),
        ),
        migrations.CreateModel(
            name="CardManaFamilyAssignment",
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
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "mana_family",
                    models.CharField(
                        choices=[
                            ("arcane", "Arcane"),
                            ("dark", "Dark"),
                            ("divine", "Divine"),
                            ("martial", "Martial"),
                            ("occult", "Occult"),
                            ("primal", "Primal"),
                        ],
                        db_index=True,
                        max_length=64,
                    ),
                ),
                (
                    "card",
                    models.ForeignKey(
                        db_column="card_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mana_family_assignments",
                        to="card_reader_core.card",
                    ),
                ),
            ],
            options={
                "db_table": "card_mana_family_assignment",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("card", "mana_family"),
                        name="uq_card_mana_family_card_family",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="cardclassificationrule",
            name="symbol",
            field=models.ForeignKey(
                blank=True,
                db_column="symbol_id",
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="classification_rules",
                to="card_reader_core.symbol",
            ),
        ),
        migrations.AlterField(
            model_name="cardclassificationrule",
            name="source_kind",
            field=models.CharField(
                choices=[("tag", "Tag"), ("type", "Type"), ("symbol", "Symbol")],
                db_index=True,
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="cardclassificationrule",
            name="target_kind",
            field=models.CharField(
                choices=[
                    ("role", "Role"),
                    ("faction", "Faction"),
                    ("mana_family", "Mana Family"),
                ],
                db_index=True,
                max_length=16,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="cardclassificationrule",
            name="ck_classification_rule_source_fk",
        ),
        migrations.AddConstraint(
            model_name="cardclassificationrule",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        source_kind="tag",
                        tag__isnull=False,
                        type__isnull=True,
                        symbol__isnull=True,
                    )
                    | models.Q(
                        source_kind="type",
                        tag__isnull=True,
                        type__isnull=False,
                        symbol__isnull=True,
                    )
                    | models.Q(
                        source_kind="symbol",
                        tag__isnull=True,
                        type__isnull=True,
                        symbol__isnull=False,
                    )
                ),
                name="ck_classification_rule_source_fk",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardclassificationrule",
            constraint=models.UniqueConstraint(
                condition=models.Q(source_kind="symbol"),
                fields=("card_pool", "target_kind", "target_key", "symbol"),
                name="uq_class_rule_symbol_target",
            ),
        ),
        migrations.AddIndex(
            model_name="cardclassificationrule",
            index=models.Index(
                fields=["card_pool", "enabled", "symbol"],
                name="ix_class_rule_pool_symbol",
            ),
        ),
        migrations.AddField(
            model_name="importjob",
            name="card_mana_family_mode",
            field=models.TextField(default="automatic"),
        ),
        migrations.AddField(
            model_name="importjob",
            name="card_mana_family_override_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="resolved_card_mana_families_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="target_card_mana_families_snapshot_json",
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(backfill_player_mana_families, migrations.RunPython.noop),
        migrations.RunPython(seed_available_symbol_rules, remove_symbol_rules_for_downgrade),
        migrations.RemoveIndex(
            model_name="cardversion",
            name="ix_cv_latest_mana_family",
        ),
        migrations.RemoveField(
            model_name="cardversion",
            name="mana_family_sort_key",
        ),
    ]

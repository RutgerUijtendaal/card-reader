from __future__ import annotations

from itertools import combinations

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


FAMILY_KEYS = ("arcane", "dark", "divine", "martial", "occult", "primal")
FAMILY_BY_SYMBOL_KEY = {
    **{f"{key}-mana": key for key in FAMILY_KEYS},
    **{f"{key}-affinity": key for key in FAMILY_KEYS},
    "primla-affinity": "primal",
}
MULTI_COMBINATIONS = sorted(
    combination
    for size in range(2, len(FAMILY_KEYS) + 1)
    for combination in combinations(range(len(FAMILY_KEYS)), size)
)
MULTI_RANKS = {
    combination: len(FAMILY_KEYS) + index
    for index, combination in enumerate(MULTI_COMBINATIONS)
}
NO_FAMILY_SORT_KEY = len(FAMILY_KEYS) + len(MULTI_COMBINATIONS)


def backfill_mana_family_sort_keys(apps: Apps, _schema_editor: BaseDatabaseSchemaEditor) -> None:
    CardVersion = apps.get_model("card_reader_core", "CardVersion")
    CardVersionSymbol = apps.get_model("card_reader_core", "CardVersionSymbol")
    ranks_by_version_id: dict[str, set[int]] = {}
    rows = CardVersionSymbol.objects.filter(symbol__key__in=FAMILY_BY_SYMBOL_KEY).values_list(
        "card_version_id",
        "symbol__key",
    )
    rank_by_family = {key: rank for rank, key in enumerate(FAMILY_KEYS)}
    for version_id, symbol_key in rows.iterator(chunk_size=2000):
        family_key = FAMILY_BY_SYMBOL_KEY[str(symbol_key)]
        ranks_by_version_id.setdefault(str(version_id), set()).add(rank_by_family[family_key])

    updates = []
    for version in CardVersion.objects.all().iterator(chunk_size=1000):
        ranks = tuple(sorted(ranks_by_version_id.get(str(version.id), set())))
        if len(ranks) == 1:
            version.mana_family_sort_key = ranks[0]
        elif len(ranks) > 1:
            version.mana_family_sort_key = MULTI_RANKS[ranks]
        else:
            version.mana_family_sort_key = NO_FAMILY_SORT_KEY
        updates.append(version)
        if len(updates) >= 1000:
            CardVersion.objects.bulk_update(updates, ["mana_family_sort_key"], batch_size=1000)
            updates.clear()
    if updates:
        CardVersion.objects.bulk_update(updates, ["mana_family_sort_key"], batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0050_merge_0049_migrations")]

    operations = [
        migrations.AddField(
            model_name="cardversion",
            name="mana_family_sort_key",
            field=models.PositiveSmallIntegerField(default=NO_FAMILY_SORT_KEY),
        ),
        migrations.RunPython(backfill_mana_family_sort_keys, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="cardversion",
            index=models.Index(fields=["is_latest", "mana_family_sort_key"], name="ix_cv_latest_mana_family"),
        ),
    ]

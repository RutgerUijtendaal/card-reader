from __future__ import annotations

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest


BASE_MIGRATION = ("card_reader_core", "0058_add_mana_card_role")
TARGET_MIGRATION = ("card_reader_core", "0059_add_mtg_like_mana_badge_ocr")


def _migrate_to(target: tuple[str, str]):
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_migration_adds_badge_ocr_to_existing_mtg_like_template() -> None:
    old_apps = _migrate_to(BASE_MIGRATION)
    Template = old_apps.get_model("card_reader_core", "Template")
    Template.objects.filter(key="mtg-like-v1").delete()
    Template.objects.create(
        key="mtg-like-v1",
        label="MTG Like V1",
        definition_json={
            "id": "mtg-like-v1",
            "version": 7,
            "regions": [
                {
                    "region_id": "top_bar",
                    "parser_type": "name_mana_cost",
                    "cut_region": {
                        "unit": "relative",
                        "x": 0.04,
                        "y": 0.02,
                        "w": 0.92,
                        "h": 0.07,
                    },
                    "ocr_config": {},
                }
            ],
        },
    )

    apps = _migrate_to(TARGET_MIGRATION)
    migrated = apps.get_model("card_reader_core", "Template").objects.get(key="mtg-like-v1")

    assert migrated.definition_json["regions"][0]["mana_badge_ocr"] == {
        "cut_region": {
            "unit": "relative",
            "x": 0.86,
            "y": 0.0,
            "w": 0.14,
            "h": 1.0,
        },
        "scales": [3, 2],
    }
    _restore_leaf()

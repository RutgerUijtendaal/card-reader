from __future__ import annotations

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest

pytestmark = pytest.mark.migration_state


BASE_MIGRATION = ("card_reader_core", "0059_backfill_card_version_rules_text")
CARD_BACK_POOL_MIGRATION = (
    "card_reader_core",
    "0060_card_back_pool_defaults_and_overrides",
)


def _migrate_to(target: tuple[str, str]):
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_current_card_back_is_adopted_for_every_pool() -> None:
    apps = _migrate_to(BASE_MIGRATION)
    CardBack = apps.get_model("card_reader_core", "CardBack")
    legacy_current = CardBack.objects.create(
        label="Legacy current",
        original_filename="legacy.png",
        source_file="uploads/card-backs/legacy.png",
        stored_path="images/legacy.webp",
        width=744,
        height=1039,
        checksum="legacy-card-back-checksum",
        is_current=True,
    )

    try:
        migrated_apps = _migrate_to(CARD_BACK_POOL_MIGRATION)
        Card = migrated_apps.get_model("card_reader_core", "Card")
        CardBackPoolDefault = migrated_apps.get_model(
            "card_reader_core", "CardBackPoolDefault"
        )
        defaults = {
            row.card_pool: row.card_back_id
            for row in CardBackPoolDefault.objects.order_by("card_pool")
        }

        assert defaults == {
            "player": legacy_current.id,
            "evil": legacy_current.id,
            "neutral": legacy_current.id,
        }
        assert "is_current" not in {
            field.name for field in migrated_apps.get_model("card_reader_core", "CardBack")._meta.fields
        }
        assert Card._meta.get_field("card_back_override").null is True
    finally:
        _restore_leaf()

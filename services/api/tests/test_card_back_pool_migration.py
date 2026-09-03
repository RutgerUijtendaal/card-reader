from __future__ import annotations

from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
import pytest

pytestmark = pytest.mark.migration_state


BASE_MIGRATION = ("card_reader_core", "0059_backfill_card_version_rules_text")
CARD_BACK_POOL_MIGRATION = (
    "card_reader_core",
    "0060_card_back_pool_defaults_and_overrides",
)
FIRE_FACTION_MIGRATION = ("card_reader_core", "0061_fire_faction")
FACTION_DEFAULT_MIGRATION = (
    "card_reader_core",
    "0062_card_back_faction_defaults",
)


def _migrate_to(target: tuple[str, str]):
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_current_card_back_is_adopted_for_every_pool_and_restored_on_rollback() -> None:
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
    player_replacement = CardBack.objects.create(
        label="Player replacement",
        original_filename="replacement.png",
        source_file="uploads/card-backs/replacement.png",
        stored_path="images/replacement.webp",
        width=744,
        height=1039,
        checksum="replacement-card-back-checksum",
        is_current=False,
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

        CardBackPoolDefault.objects.filter(card_pool="player").update(
            card_back_id=player_replacement.id
        )
        rolled_back_apps = _migrate_to(BASE_MIGRATION)
        LegacyCardBack = rolled_back_apps.get_model("card_reader_core", "CardBack")
        assert LegacyCardBack.objects.get(id=player_replacement.id).is_current is True
        assert LegacyCardBack.objects.get(id=legacy_current.id).is_current is False
    finally:
        _restore_leaf()


@pytest.mark.django_db(transaction=True)
def test_faction_default_migration_rejects_rollback_with_assignments() -> None:
    apps = _migrate_to(FACTION_DEFAULT_MIGRATION)
    CardBack = apps.get_model("card_reader_core", "CardBack")
    CardBackFactionDefault = apps.get_model(
        "card_reader_core",
        "CardBackFactionDefault",
    )
    card_back = CardBack.objects.create(
        label="Order default",
        original_filename="order.png",
        source_file="uploads/card-backs/order.png",
        stored_path="images/order.webp",
        width=744,
        height=1039,
        checksum="order-card-back-checksum",
    )
    CardBackFactionDefault.objects.create(faction="order", card_back=card_back)

    try:
        with pytest.raises(IrreversibleError, match="faction-default assignments exist"):
            _migrate_to(FIRE_FACTION_MIGRATION)
    finally:
        _restore_leaf()

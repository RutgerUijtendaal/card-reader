from __future__ import annotations

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest

pytestmark = pytest.mark.migration_state


BASE_MIGRATION = ("card_reader_core", "0058_deck_description_markup")
RULE_TEXT_MIGRATION = ("card_reader_core", "0059_backfill_card_version_rules_text")


def _migrate_to(target: tuple[str, str]):
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_rule_text_migration_rebuilds_persisted_plain_text() -> None:
    apps = _migrate_to(BASE_MIGRATION)
    Card = apps.get_model("card_reader_core", "Card")
    CardVersion = apps.get_model("card_reader_core", "CardVersion")
    CardVersionSymbol = apps.get_model("card_reader_core", "CardVersionSymbol")
    Symbol = apps.get_model("card_reader_core", "Symbol")
    Template = apps.get_model("card_reader_core", "Template")

    template = Template.objects.create(key="markup-migration", label="Markup Migration")
    card = Card.objects.create(
        key="markup-migration-card",
        label="Markup Migration Card",
        card_pool="player",
    )
    version = CardVersion.objects.create(
        card_id=card.id,
        template_id=template.id,
        image_hash="markup-migration-hash",
        rules_text_enriched=(
            "Deal **five** damage with [[symbol:fire]].\n\n"
            "`[[symbol:fire]]` and [[card:other|Other Card]]."
        ),
        rules_text="stale plain text",
    )
    symbol = Symbol.objects.create(
        key="fire",
        label="Fire",
        text_token="{F}",
    )
    CardVersionSymbol.objects.create(card_version_id=version.id, symbol_id=symbol.id)

    try:
        migrated_apps = _migrate_to(RULE_TEXT_MIGRATION)
        migrated_version = migrated_apps.get_model(
            "card_reader_core", "CardVersion"
        ).objects.get(id=version.id)

        assert migrated_version.rules_text == (
            "Deal five damage with {F}.\n\n[[symbol:fire]] and Other Card."
        )
    finally:
        _restore_leaf()

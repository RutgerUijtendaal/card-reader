from __future__ import annotations

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest


@pytest.mark.django_db(transaction=True)
def test_card_classification_migration_backfills_and_reverses_hero_roles() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0053_deck_creation")])
    old_apps = executor.loader.project_state([("card_reader_core", "0053_deck_creation")]).apps
    OldCard = old_apps.get_model("card_reader_core", "Card")
    hero = OldCard.objects.create(key="migration-hero", label="Migration Hero", is_hero=True)
    standard = OldCard.objects.create(key="migration-standard", label="Migration Standard", is_hero=False)

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0054_card_classification")])
    new_apps = executor.loader.project_state([("card_reader_core", "0054_card_classification")]).apps
    NewCard = new_apps.get_model("card_reader_core", "Card")
    CardRoleAssignment = new_apps.get_model("card_reader_core", "CardRoleAssignment")

    assert NewCard.objects.get(id=hero.id).card_pool == "player"
    assert NewCard.objects.get(id=standard.id).card_pool == "player"
    assert CardRoleAssignment.objects.filter(card_id=hero.id, role="hero").exists()
    assert not CardRoleAssignment.objects.filter(card_id=standard.id).exists()

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0053_deck_creation")])
    reversed_apps = executor.loader.project_state([("card_reader_core", "0053_deck_creation")]).apps
    ReversedCard = reversed_apps.get_model("card_reader_core", "Card")

    assert ReversedCard.objects.get(id=hero.id).is_hero is True
    assert ReversedCard.objects.get(id=standard.id).is_hero is False

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

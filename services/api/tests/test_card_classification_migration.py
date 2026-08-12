from __future__ import annotations

from django.db import IntegrityError, connection, transaction
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


@pytest.mark.django_db(transaction=True)
def test_location_role_migration_widens_role_keys_and_preserves_uniqueness() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0056_import_classification_inference")])
    old_apps = executor.loader.project_state(
        [("card_reader_core", "0056_import_classification_inference")]
    ).apps
    OldCard = old_apps.get_model("card_reader_core", "Card")
    card = OldCard.objects.create(key="migration-location", label="Migration Location")

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0057_location_card_role")])
    new_apps = executor.loader.project_state(
        [("card_reader_core", "0057_location_card_role")]
    ).apps
    CardRoleAssignment = new_apps.get_model("card_reader_core", "CardRoleAssignment")
    role_field = CardRoleAssignment._meta.get_field("role")

    assert role_field.max_length == 64
    assert ("location", "Location") in role_field.choices
    CardRoleAssignment.objects.create(card_id=card.id, role="location")
    with pytest.raises(IntegrityError), transaction.atomic():
        CardRoleAssignment.objects.create(card_id=card.id, role="location")

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0056_import_classification_inference")])
    reversed_apps = executor.loader.project_state(
        [("card_reader_core", "0056_import_classification_inference")]
    ).apps
    ReversedRoleAssignment = reversed_apps.get_model("card_reader_core", "CardRoleAssignment")
    assert ReversedRoleAssignment._meta.get_field("role").max_length == 16

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_pool_scoped_identity_migration_backfills_aliases_and_allows_cross_pool_twins() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0057_location_card_role")])
    old_apps = executor.loader.project_state([("card_reader_core", "0057_location_card_role")]).apps
    OldCard = old_apps.get_model("card_reader_core", "Card")
    OldCardAlias = old_apps.get_model("card_reader_core", "CardAlias")
    player = OldCard.objects.create(key="shared-name", label="Shared Name", card_pool="player")
    alias = OldCardAlias.objects.create(card_id=player.id, key="shared-alias", label="Shared Alias")

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0058_pool_scoped_card_identity")])
    apps = executor.loader.project_state(
        [("card_reader_core", "0058_pool_scoped_card_identity")]
    ).apps
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")

    assert CardAlias.objects.get(id=alias.id).card_pool == "player"
    evil = Card.objects.create(key="shared-name", label="Shared Name", card_pool="evil")
    neutral = Card.objects.create(key="shared-name", label="Shared Name", card_pool="neutral")
    CardAlias.objects.create(card_id=evil.id, card_pool="evil", key="shared-alias", label="Shared Alias")
    CardAlias.objects.create(
        card_id=neutral.id,
        card_pool="neutral",
        key="shared-alias",
        label="Shared Alias",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Card.objects.create(key="shared-name", label="Duplicate", card_pool="evil")
    with pytest.raises(IntegrityError), transaction.atomic():
        CardAlias.objects.create(
            card_id=evil.id,
            card_pool="evil",
            key="shared-alias",
            label="Duplicate",
        )

    assert Card._meta.get_field("key").unique is False
    assert CardAlias._meta.get_field("key").unique is False
    assert CardAlias._meta.get_field("card_pool").null is False

    CardAlias.objects.filter(card_pool__in=["evil", "neutral"]).delete()
    Card.objects.filter(card_pool__in=["evil", "neutral"]).delete()
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0057_location_card_role")])
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_pool_scoped_identity_migration_rejects_temporary_game_master_values() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0057_location_card_role")])
    old_apps = executor.loader.project_state([("card_reader_core", "0057_location_card_role")]).apps
    OldCard = old_apps.get_model("card_reader_core", "Card")
    invalid = OldCard.objects.create(key="temporary-gm", label="Temporary GM", card_pool="game_master")

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="intentionally does not guess Evil versus Neutral"):
        executor.migrate([("card_reader_core", "0058_pool_scoped_card_identity")])

    OldCard.objects.filter(id=invalid.id).delete()
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_pool_scoped_identity_migration_rejects_primary_alias_collisions() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0057_location_card_role")])
    old_apps = executor.loader.project_state([("card_reader_core", "0057_location_card_role")]).apps
    OldCard = old_apps.get_model("card_reader_core", "Card")
    OldCardAlias = old_apps.get_model("card_reader_core", "CardAlias")
    primary = OldCard.objects.create(key="forward-collision", label="Primary", card_pool="player")
    alias_owner = OldCard.objects.create(key="forward-alias-owner", label="Alias Owner", card_pool="player")
    alias = OldCardAlias.objects.create(
        card_id=alias_owner.id,
        key=primary.key,
        label="Conflicting Alias",
    )

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="another card's alias"):
        executor.migrate([("card_reader_core", "0058_pool_scoped_card_identity")])

    OldCardAlias.objects.filter(id=alias.id).delete()
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_pool_scoped_identity_reverse_rejects_primary_alias_collisions() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0058_pool_scoped_card_identity")])
    apps = executor.loader.project_state(
        [("card_reader_core", "0058_pool_scoped_card_identity")]
    ).apps
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    primary = Card.objects.create(key="reverse-collision", label="Primary", card_pool="player")
    alias_owner = Card.objects.create(key="alias-owner", label="Alias Owner", card_pool="player")
    alias = CardAlias.objects.create(
        card_id=alias_owner.id,
        card_pool="player",
        key=primary.key,
        label="Collision",
    )

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="primary card key also exists as an alias"):
        executor.migrate([("card_reader_core", "0057_location_card_role")])

    CardAlias.objects.filter(id=alias.id).delete()
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0057_location_card_role")])
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

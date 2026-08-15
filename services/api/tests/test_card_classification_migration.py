from __future__ import annotations

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
import pytest


BASE_MIGRATION = ("card_reader_core", "0053_deck_creation")
FINAL_MIGRATION = ("card_reader_core", "0054_card_classification_final_state")


def _migrate_to(target: tuple[str, str]):
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_final_state_migration_backfills_master_data_and_reverses_hero_roles() -> None:
    old_apps = _migrate_to(BASE_MIGRATION)
    Card = old_apps.get_model("card_reader_core", "Card")
    CardAlias = old_apps.get_model("card_reader_core", "CardAlias")
    ImportJob = old_apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = old_apps.get_model("card_reader_core", "ImportJobItem")
    Template = old_apps.get_model("card_reader_core", "Template")
    TtsCardSheet = old_apps.get_model("card_reader_core", "TtsCardSheet")
    TtsCardSheetSlot = old_apps.get_model("card_reader_core", "TtsCardSheetSlot")

    hero = Card.objects.create(key="migration-hero", label="Migration Hero", is_hero=True)
    standard = Card.objects.create(
        key="migration-standard",
        label="Migration Standard",
        is_hero=False,
    )
    alias = CardAlias.objects.create(
        card_id=hero.id,
        key="migration-hero-alias",
        label="Migration Hero Alias",
    )
    template = Template.objects.create(key="migration-template", label="Migration Template")
    job = ImportJob.objects.create(source_path="migration", template_id=template.id)
    item = ImportJobItem.objects.create(
        job_id=job.id,
        source_file="migration.png",
        warning_code="legacy_warning",
        warning_message="Legacy warning message.",
    )
    sheet = TtsCardSheet.objects.create(sequence=991)
    slot = TtsCardSheetSlot.objects.create(
        sheet_id=sheet.id,
        slot_index=0,
        card_identity_id="migration-card-identity",
    )

    new_apps = _migrate_to(FINAL_MIGRATION)
    NewCard = new_apps.get_model("card_reader_core", "Card")
    NewAlias = new_apps.get_model("card_reader_core", "CardAlias")
    CardIdentityPoolLock = new_apps.get_model("card_reader_core", "CardIdentityPoolLock")
    CardRoleAssignment = new_apps.get_model("card_reader_core", "CardRoleAssignment")
    NewImportJob = new_apps.get_model("card_reader_core", "ImportJob")
    NewImportJobItem = new_apps.get_model("card_reader_core", "ImportJobItem")
    NewSheet = new_apps.get_model("card_reader_core", "TtsCardSheet")
    NewSlot = new_apps.get_model("card_reader_core", "TtsCardSheetSlot")

    migrated_hero = NewCard.objects.get(id=hero.id)
    assert migrated_hero.card_pool == "player"
    assert migrated_hero.faction_identity_key == "[]"
    assert NewCard.objects.get(id=standard.id).card_pool == "player"
    assert CardRoleAssignment.objects.filter(card_id=hero.id, role="hero").exists()
    assert not CardRoleAssignment.objects.filter(card_id=standard.id).exists()

    migrated_alias = NewAlias.objects.get(id=alias.id)
    assert migrated_alias.card_pool == "player"
    assert migrated_alias.faction_identity_key == "[]"
    assert set(CardIdentityPoolLock.objects.values_list("card_pool", flat=True)) == {
        "player",
        "evil",
        "neutral",
    }

    assert NewImportJob.objects.get(id=job.id).creation_key
    assert NewImportJob.objects.get(id=job.id).card_pool == "player"
    assert NewImportJobItem.objects.get(id=item.id).warnings_json == [
        {"code": "legacy_warning", "message": "Legacy warning message."}
    ]
    assert NewSheet.objects.get(id=sheet.id).card_pool == "player"
    assert NewSlot.objects.get(id=slot.id).card_pool == "player"

    reversed_apps = _migrate_to(BASE_MIGRATION)
    ReversedCard = reversed_apps.get_model("card_reader_core", "Card")
    assert ReversedCard.objects.get(id=hero.id).is_hero is True
    assert ReversedCard.objects.get(id=standard.id).is_hero is False

    _restore_leaf()


@pytest.mark.django_db(transaction=True)
def test_final_state_migration_rejects_primary_alias_collisions() -> None:
    old_apps = _migrate_to(BASE_MIGRATION)
    Card = old_apps.get_model("card_reader_core", "Card")
    CardAlias = old_apps.get_model("card_reader_core", "CardAlias")
    primary = Card.objects.create(key="migration-collision", label="Primary")
    aliased = Card.objects.create(key="migration-aliased", label="Aliased")
    alias = CardAlias.objects.create(
        card_id=aliased.id,
        key=primary.key,
        label="Collision",
    )

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="primary card key also exists"):
        executor.migrate([FINAL_MIGRATION])

    CardAlias.objects.filter(id=alias.id).delete()
    _restore_leaf()


@pytest.mark.django_db(transaction=True)
def test_final_state_identity_constraints_allow_only_distinct_namespaces() -> None:
    apps = _migrate_to(FINAL_MIGRATION)
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")

    player = Card.objects.create(key="shared-key", label="Player", card_pool="player")
    evil = Card.objects.create(key="shared-key", label="Evil", card_pool="evil")
    faction = Card.objects.create(
        key="shared-key",
        label="Evil Order",
        card_pool="evil",
        faction_identity_key='["order"]',
    )
    CardAlias.objects.create(
        card_id=player.id,
        card_pool="player",
        faction_identity_key="[]",
        key="shared-alias",
        label="Player alias",
    )
    CardAlias.objects.create(
        card_id=evil.id,
        card_pool="evil",
        faction_identity_key="[]",
        key="shared-alias",
        label="Evil alias",
    )
    CardAlias.objects.create(
        card_id=faction.id,
        card_pool="evil",
        faction_identity_key='["order"]',
        key="shared-alias",
        label="Evil Order alias",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Card.objects.create(key="shared-key", label="Duplicate", card_pool="evil")
    with pytest.raises(IntegrityError), transaction.atomic():
        CardAlias.objects.create(
            card_id=evil.id,
            card_pool="evil",
            faction_identity_key="[]",
            key="shared-alias",
            label="Duplicate alias",
        )

    _restore_leaf()


@pytest.mark.django_db(transaction=True)
def test_final_state_tts_slots_are_partitioned_by_pool() -> None:
    apps = _migrate_to(FINAL_MIGRATION)
    Sheet = apps.get_model("card_reader_core", "TtsCardSheet")
    Slot = apps.get_model("card_reader_core", "TtsCardSheetSlot")
    player_sheet = Sheet.objects.create(sequence=992, card_pool="player")
    evil_sheet = Sheet.objects.create(sequence=993, card_pool="evil")
    Slot.objects.create(
        sheet_id=player_sheet.id,
        card_pool="player",
        slot_index=0,
        card_identity_id="shared-card-identity",
    )
    Slot.objects.create(
        sheet_id=evil_sheet.id,
        card_pool="evil",
        slot_index=0,
        card_identity_id="shared-card-identity",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Slot.objects.create(
            sheet_id=evil_sheet.id,
            card_pool="evil",
            slot_index=1,
            card_identity_id="shared-card-identity",
        )

    _restore_leaf()

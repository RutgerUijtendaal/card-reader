from __future__ import annotations

import hashlib
import json

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
import pytest


def _classification_snapshot_digest(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@pytest.mark.django_db(transaction=True)
def test_card_classification_migration_backfills_and_reverses_hero_roles() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0053_deck_creation")])
    old_apps = executor.loader.project_state([("card_reader_core", "0053_deck_creation")]).apps
    OldCard = old_apps.get_model("card_reader_core", "Card")
    hero = OldCard.objects.create(key="migration-hero", label="Migration Hero", is_hero=True)
    standard = OldCard.objects.create(
        key="migration-standard", label="Migration Standard", is_hero=False
    )

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0054_card_classification")])
    new_apps = executor.loader.project_state(
        [("card_reader_core", "0054_card_classification")]
    ).apps
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
    new_apps = executor.loader.project_state([("card_reader_core", "0057_location_card_role")]).apps
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
    CardAlias.objects.create(
        card_id=evil.id, card_pool="evil", key="shared-alias", label="Shared Alias"
    )
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
def test_card_identity_pool_lock_migration_seeds_every_pool() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0058_pool_scoped_card_identity")])
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])
    apps = executor.loader.project_state(
        [("card_reader_core", "0059_card_identity_pool_locks")]
    ).apps
    CardIdentityPoolLock = apps.get_model("card_reader_core", "CardIdentityPoolLock")

    assert set(CardIdentityPoolLock.objects.values_list("card_pool", flat=True)) == {
        "player",
        "evil",
        "neutral",
    }

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_pool_scoped_identity_migration_rejects_temporary_game_master_values() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0057_location_card_role")])
    old_apps = executor.loader.project_state([("card_reader_core", "0057_location_card_role")]).apps
    OldCard = old_apps.get_model("card_reader_core", "Card")
    invalid = OldCard.objects.create(
        key="temporary-gm", label="Temporary GM", card_pool="game_master"
    )

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
    alias_owner = OldCard.objects.create(
        key="forward-alias-owner", label="Alias Owner", card_pool="player"
    )
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


@pytest.mark.django_db(transaction=True)
def test_faction_classification_migration_backfills_empty_namespace_and_nests_evidence() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])
    old_apps = executor.loader.project_state(
        [("card_reader_core", "0059_card_identity_pool_locks")]
    ).apps
    OldCard = old_apps.get_model("card_reader_core", "Card")
    OldCardAlias = old_apps.get_model("card_reader_core", "CardAlias")
    OldTemplate = old_apps.get_model("card_reader_core", "Template")
    OldImportJob = old_apps.get_model("card_reader_core", "ImportJob")
    OldImportJobItem = old_apps.get_model("card_reader_core", "ImportJobItem")
    card = OldCard.objects.create(key="factionless", label="Factionless")
    alias = OldCardAlias.objects.create(
        card_id=card.id,
        card_pool="player",
        key="old-factionless",
        label="Old Factionless",
    )
    template = OldTemplate.objects.create(key="migration-template", label="Migration")
    job = OldImportJob.objects.create(source_path="imports/migration", template_id=template.id)
    item = OldImportJobItem.objects.create(
        job_id=job.id,
        source_file="imports/migration/card.webp",
        card_role_inference_json={
            "mode": "automatic",
            "resolved_roles": ["hero"],
            "live_classification": {"card_pool": "player", "card_roles": ["hero"]},
        },
    )
    empty_evidence_item = OldImportJobItem.objects.create(
        job_id=job.id,
        source_file="imports/migration/unclassified.webp",
        card_role_inference_json={},
    )

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0060_faction_classification")])
    apps = executor.loader.project_state([("card_reader_core", "0060_faction_classification")]).apps
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    CardFactionAssignment = apps.get_model("card_reader_core", "CardFactionAssignment")
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")

    assert Card.objects.get(id=card.id).faction_identity_key == "[]"
    assert CardAlias.objects.get(id=alias.id).faction_identity_key == "[]"
    migrated_evidence = ImportJobItem.objects.get(id=item.id).classification_inference_json
    assert migrated_evidence["roles"]["resolved_roles"] == ["hero"]
    assert migrated_evidence["factions"] == {}
    assert migrated_evidence["live_classification"] == {
        "card_pool": "player",
        "card_roles": ["hero"],
    }
    assert ImportJobItem.objects.get(id=empty_evidence_item.id).classification_inference_json == {}
    assert CardFactionAssignment._meta.get_field("faction").max_length == 64
    assert CardRoleAssignment._meta.get_field("role").choices == [
        ("hero", "Hero"),
        ("boss", "Boss"),
        ("location", "Location"),
        ("boon", "Boon"),
        ("event", "Event"),
        ("shop_item", "Shop Item"),
    ]

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])
    reversed_apps = executor.loader.project_state(
        [("card_reader_core", "0059_card_identity_pool_locks")]
    ).apps
    ReversedItem = reversed_apps.get_model("card_reader_core", "ImportJobItem")
    assert ReversedItem.objects.get(id=item.id).card_role_inference_json["resolved_roles"] == [
        "hero"
    ]
    assert ReversedItem.objects.get(id=empty_evidence_item.id).card_role_inference_json == {}
    OldImportJob.objects.filter(id=job.id).update(status="completed")
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_faction_classification_reverse_rejects_faction_data() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0060_faction_classification")])
    apps = executor.loader.project_state([("card_reader_core", "0060_faction_classification")]).apps
    Card = apps.get_model("card_reader_core", "Card")
    CardFactionAssignment = apps.get_model("card_reader_core", "CardFactionAssignment")
    card = Card.objects.create(
        key="order-card",
        label="Order Card",
        faction_identity_key='["order"]',
    )
    assignment = CardFactionAssignment.objects.create(card_id=card.id, faction="order")

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="cannot be reversed while classification data exists"):
        executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])

    CardFactionAssignment.objects.filter(id=assignment.id).delete()
    Card.objects.filter(id=card.id).delete()
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_faction_classification_reverse_rejects_new_role_data() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0060_faction_classification")])
    apps = executor.loader.project_state([("card_reader_core", "0060_faction_classification")]).apps
    Card = apps.get_model("card_reader_core", "Card")
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    Template = apps.get_model("card_reader_core", "Template")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")
    card = Card.objects.create(key="new-role-card", label="New Role Card")
    assignment = CardRoleAssignment.objects.create(card_id=card.id, role="boss")

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="new card role assignments"):
        executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])

    CardRoleAssignment.objects.filter(id=assignment.id).delete()
    template = Template.objects.create(
        key="new-role-template",
        label="New Role Template",
        inferred_card_roles_json=["shop_item"],
    )
    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="new template role hints"):
        executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])

    Template.objects.filter(id=template.id).update(inferred_card_roles_json=[])
    job = ImportJob.objects.create(
        source_path="imports/new-role",
        template_id=template.id,
        classification_inference_policy_version=2,
    )
    item = ImportJobItem.objects.create(
        job_id=job.id,
        source_file="imports/new-role/card.webp",
        classification_inference_json={
            "queued_target_classification": {"card_roles": ["boss"]}
        },
    )
    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="new import item role snapshots"):
        executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])

    ImportJobItem.objects.filter(id=item.id).update(classification_inference_json={})
    ImportJob.objects.filter(id=job.id).update(status="completed")
    Card.objects.filter(id=card.id).delete()
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_faction_classification_reverse_rejects_policy_version_three_jobs() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0060_faction_classification")])
    apps = executor.loader.project_state([("card_reader_core", "0060_faction_classification")]).apps
    Template = apps.get_model("card_reader_core", "Template")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    template = Template.objects.create(key="policy-three-template", label="Policy Three")
    job = ImportJob.objects.create(
        source_path="imports/policy-three",
        template_id=template.id,
        classification_inference_policy_version=3,
    )

    executor = MigrationExecutor(connection)
    with pytest.raises(
        RuntimeError,
        match="classification policy versions newer than 2",
    ):
        executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])

    ImportJob.objects.filter(id=job.id).update(
        classification_inference_policy_version=2,
        status="completed",
    )
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0059_card_identity_pool_locks")])
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_admin_owned_classification_rule_migration_preflights_jobs_and_removes_hints() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0060_faction_classification")])
    old_apps = executor.loader.project_state(
        [("card_reader_core", "0060_faction_classification")]
    ).apps
    Template = old_apps.get_model("card_reader_core", "Template")
    ImportJob = old_apps.get_model("card_reader_core", "ImportJob")
    template = Template.objects.create(
        key="classification-rule-migration",
        label="Classification Rule Migration",
        inferred_card_roles_json=["hero"],
        inferred_card_factions_json=["order"],
    )
    job = ImportJob.objects.create(
        source_path="imports/classification-rule-migration",
        template_id=template.id,
        status="queued",
    )

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="Finish, cancel, or reset these jobs first"):
        executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])

    ImportJob.objects.filter(id=job.id).update(status="completed")
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])
    apps = executor.loader.project_state(
        [("card_reader_core", "0061_admin_owned_classification_rules")]
    ).apps
    NewTemplate = apps.get_model("card_reader_core", "Template")
    NewImportJob = apps.get_model("card_reader_core", "ImportJob")
    Rule = apps.get_model("card_reader_core", "CardClassificationRule")
    Tag = apps.get_model("card_reader_core", "Tag")

    assert "inferred_card_roles_json" not in {
        field.name for field in NewTemplate._meta.get_fields()
    }
    assert "inferred_card_factions_json" not in {
        field.name for field in NewTemplate._meta.get_fields()
    }
    job_fields = {field.name for field in NewImportJob._meta.get_fields()}
    assert "classification_rule_snapshot_json" in job_fields
    assert "classification_inference_policy_version" not in job_fields
    tag = Tag.objects.create(key="migration-rule-tag", label="Migration Rule Tag")
    Rule.objects.create(
        card_pool="player",
        target_kind="role",
        target_key="hero",
        source_kind="tag",
        tag_id=tag.id,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Rule.objects.create(
            card_pool="player",
            target_kind="role",
            target_key="hero",
            source_kind="tag",
            tag_id=tag.id,
        )

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="while classification rules exist"):
        executor.migrate([("card_reader_core", "0060_faction_classification")])

    Rule.objects.all().delete()
    NewImportJob.objects.filter(id=job.id).update(
        classification_rule_snapshot_json={"schema_version": 1, "digest": "preserved"}
    )
    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="retain classification rule snapshots"):
        executor.migrate([("card_reader_core", "0060_faction_classification")])

    NewImportJob.objects.filter(id=job.id).update(classification_rule_snapshot_json={})
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0060_faction_classification")])

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_pool_partitioned_tts_sheet_migration_backfills_and_guards_reverse() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])
    old_apps = executor.loader.project_state(
        [("card_reader_core", "0061_admin_owned_classification_rules")]
    ).apps
    OldSheet = old_apps.get_model("card_reader_core", "TtsCardSheet")
    OldSlot = old_apps.get_model("card_reader_core", "TtsCardSheetSlot")
    player_sheet = OldSheet.objects.create(sequence=991)
    OldSlot.objects.create(
        sheet_id=player_sheet.id,
        slot_index=0,
        card_identity_id="shared-card-identity",
    )

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0062_pool_partitioned_tts_card_sheets")])
    apps = executor.loader.project_state(
        [("card_reader_core", "0062_pool_partitioned_tts_card_sheets")]
    ).apps
    Sheet = apps.get_model("card_reader_core", "TtsCardSheet")
    Slot = apps.get_model("card_reader_core", "TtsCardSheetSlot")
    player_slot = Slot.objects.get(card_identity_id="shared-card-identity")
    assert player_slot.card_pool == "player"
    assert player_slot.sheet.card_pool == "player"

    evil_sheet = Sheet.objects.create(sequence=992, card_pool="evil")
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

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="while Evil or Neutral sheet data exists"):
        executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])

    Slot.objects.filter(card_pool="evil").delete()
    Sheet.objects.filter(card_pool="evil").delete()
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_dark_faction_migration_rewrites_identity_rules_and_import_history() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])
    old_apps = executor.loader.project_state(
        [("card_reader_core", "0061_admin_owned_classification_rules")]
    ).apps
    Card = old_apps.get_model("card_reader_core", "Card")
    CardAlias = old_apps.get_model("card_reader_core", "CardAlias")
    CardFactionAssignment = old_apps.get_model("card_reader_core", "CardFactionAssignment")
    CardClassificationRule = old_apps.get_model("card_reader_core", "CardClassificationRule")
    ImportJob = old_apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = old_apps.get_model("card_reader_core", "ImportJobItem")
    Tag = old_apps.get_model("card_reader_core", "Tag")
    Template = old_apps.get_model("card_reader_core", "Template")

    card = Card.objects.create(
        key="migration-dark-card",
        label="Migration Dark Card",
        card_pool="evil",
        faction_identity_key='["order","darkness"]',
    )
    CardFactionAssignment.objects.bulk_create(
        [
            CardFactionAssignment(card_id=card.id, faction="order"),
            CardFactionAssignment(card_id=card.id, faction="darkness"),
        ]
    )
    alias = CardAlias.objects.create(
        card_id=card.id,
        card_pool="evil",
        faction_identity_key='["order","darkness"]',
        key="migration-dark-alias",
        label="Migration Dark Alias",
    )
    dark_tag = Tag.objects.create(key="dark", label="Dark", identifiers_json=["dark"])
    rule = CardClassificationRule.objects.create(
        card_pool="evil",
        target_kind="faction",
        target_key="darkness",
        source_kind="tag",
        tag_id=dark_tag.id,
    )
    snapshot_rule = {
        "rule_id": rule.id,
        "card_pool": "evil",
        "source_kind": "tag",
        "source_id": dark_tag.id,
        "source_key": "dark",
        "source_label": "Dark",
        "source_identifiers": ["dark"],
        "target_kind": "faction",
        "target_key": "darkness",
    }
    snapshot_body: dict[str, object] = {
        "schema_version": 1,
        "card_pool": "evil",
        "rules": [snapshot_rule],
    }
    old_digest = _classification_snapshot_digest(snapshot_body)
    template = Template.objects.create(key="migration-dark-template", label="Migration Dark")
    job = ImportJob.objects.create(
        source_path="imports/migration-dark",
        template_id=template.id,
        card_pool="evil",
        card_faction_mode="override",
        card_faction_override_json=["darkness"],
        classification_rule_snapshot_json={**snapshot_body, "digest": old_digest},
        status="completed",
    )
    item = ImportJobItem.objects.create(
        job_id=job.id,
        source_file="imports/migration-dark/card.webp",
        status="completed",
        resolved_card_factions_json=["order", "darkness"],
        target_card_factions_snapshot_json=["darkness"],
        classification_inference_json={
            "roles": {"snapshot_digest": old_digest},
            "factions": {
                "matched_rules": [snapshot_rule],
                "override_factions": ["darkness"],
                "resolved_factions": ["order", "darkness"],
                "snapshot_digest": old_digest,
            },
            "live_classification": {"card_factions": ["order", "darkness"]},
            "queued_target_classification": {"card_factions": ["darkness"]},
        },
        warnings_json=[
            {
                "code": "card_classification_mismatch",
                "details": {
                    "inferred": {"card_factions": ["order", "darkness"]},
                    "existing": {"card_factions": ["darkness"]},
                },
            }
        ],
    )

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0062_dark_and_metal_factions")])
    apps = executor.loader.project_state(
        [("card_reader_core", "0062_dark_and_metal_factions")]
    ).apps
    MigratedCard = apps.get_model("card_reader_core", "Card")
    MigratedAlias = apps.get_model("card_reader_core", "CardAlias")
    MigratedAssignment = apps.get_model("card_reader_core", "CardFactionAssignment")
    MigratedRule = apps.get_model("card_reader_core", "CardClassificationRule")
    MigratedJob = apps.get_model("card_reader_core", "ImportJob")
    MigratedItem = apps.get_model("card_reader_core", "ImportJobItem")

    assert MigratedAssignment._meta.get_field("faction").choices == [
        ("order", "Order"),
        ("blood", "Blood"),
        ("dark", "Dark"),
        ("metal", "Metal"),
    ]
    assert set(
        MigratedAssignment.objects.filter(card_id=card.id).values_list("faction", flat=True)
    ) == {"order", "dark"}
    assert MigratedCard.objects.get(id=card.id).faction_identity_key == '["order","dark"]'
    assert MigratedAlias.objects.get(id=alias.id).faction_identity_key == '["order","dark"]'
    migrated_rule = MigratedRule.objects.select_related("tag").get(id=rule.id)
    assert migrated_rule.target_key == "dark"
    assert migrated_rule.tag.key == "dark"
    migrated_job = MigratedJob.objects.get(id=job.id)
    migrated_snapshot = migrated_job.classification_rule_snapshot_json
    new_digest = migrated_snapshot["digest"]
    assert migrated_job.card_faction_override_json == ["dark"]
    assert migrated_snapshot["rules"][0]["target_key"] == "dark"
    assert migrated_snapshot["rules"][0]["source_key"] == "dark"
    assert new_digest != old_digest
    assert new_digest == _classification_snapshot_digest(
        {
            "schema_version": migrated_snapshot["schema_version"],
            "card_pool": migrated_snapshot["card_pool"],
            "rules": migrated_snapshot["rules"],
        }
    )
    migrated_item = MigratedItem.objects.get(id=item.id)
    assert migrated_item.resolved_card_factions_json == ["order", "dark"]
    assert migrated_item.target_card_factions_snapshot_json == ["dark"]
    assert migrated_item.classification_inference_json["roles"]["snapshot_digest"] == new_digest
    faction_evidence = migrated_item.classification_inference_json["factions"]
    assert faction_evidence["matched_rules"][0]["target_key"] == "dark"
    assert faction_evidence["matched_rules"][0]["source_key"] == "dark"
    assert faction_evidence["override_factions"] == ["dark"]
    assert faction_evidence["resolved_factions"] == ["order", "dark"]
    assert faction_evidence["snapshot_digest"] == new_digest
    assert migrated_item.warnings_json[0]["details"]["inferred"]["card_factions"] == [
        "order",
        "dark",
    ]

    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])
    reversed_apps = executor.loader.project_state(
        [("card_reader_core", "0061_admin_owned_classification_rules")]
    ).apps
    ReversedCard = reversed_apps.get_model("card_reader_core", "Card")
    ReversedAlias = reversed_apps.get_model("card_reader_core", "CardAlias")
    ReversedAssignment = reversed_apps.get_model("card_reader_core", "CardFactionAssignment")
    ReversedRule = reversed_apps.get_model("card_reader_core", "CardClassificationRule")
    ReversedJob = reversed_apps.get_model("card_reader_core", "ImportJob")
    ReversedItem = reversed_apps.get_model("card_reader_core", "ImportJobItem")
    assert set(
        ReversedAssignment.objects.filter(card_id=card.id).values_list("faction", flat=True)
    ) == {"order", "darkness"}
    assert ReversedCard.objects.get(id=card.id).faction_identity_key == '["order","darkness"]'
    assert ReversedAlias.objects.get(id=alias.id).faction_identity_key == '["order","darkness"]'
    assert ReversedRule.objects.get(id=rule.id).target_key == "darkness"
    reversed_job = ReversedJob.objects.get(id=job.id)
    assert reversed_job.card_faction_override_json == ["darkness"]
    assert reversed_job.classification_rule_snapshot_json["digest"] == old_digest
    reversed_item = ReversedItem.objects.get(id=item.id)
    assert reversed_item.resolved_card_factions_json == ["order", "darkness"]
    assert reversed_item.target_card_factions_snapshot_json == ["darkness"]
    assert reversed_item.classification_inference_json["roles"]["snapshot_digest"] == old_digest
    assert reversed_item.classification_inference_json["factions"]["snapshot_digest"] == old_digest

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_dark_faction_migration_preflights_non_terminal_imports() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])
    apps = executor.loader.project_state(
        [("card_reader_core", "0061_admin_owned_classification_rules")]
    ).apps
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    Template = apps.get_model("card_reader_core", "Template")
    template = Template.objects.create(key="migration-active-template", label="Migration Active")
    job = ImportJob.objects.create(
        source_path="imports/migration-active",
        template_id=template.id,
        status="queued",
    )

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="cannot be renamed while import jobs are non-terminal"):
        executor.migrate([("card_reader_core", "0062_dark_and_metal_factions")])

    ImportJob.objects.filter(id=job.id).update(status="completed")
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_dark_faction_migration_reverse_rejects_metal_data() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0062_dark_and_metal_factions")])
    apps = executor.loader.project_state(
        [("card_reader_core", "0062_dark_and_metal_factions")]
    ).apps
    Card = apps.get_model("card_reader_core", "Card")
    CardFactionAssignment = apps.get_model("card_reader_core", "CardFactionAssignment")
    card = Card.objects.create(
        key="migration-metal-card",
        label="Migration Metal Card",
        card_pool="evil",
        faction_identity_key='["metal"]',
    )
    CardFactionAssignment.objects.create(card_id=card.id, faction="metal")

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="cannot be reversed while Metal faction data exists"):
        executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])

    Card.objects.filter(id=card.id).delete()
    executor = MigrationExecutor(connection)
    executor.migrate([("card_reader_core", "0061_admin_owned_classification_rules")])
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

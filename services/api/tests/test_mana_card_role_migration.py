from __future__ import annotations

from typing import Any

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest


BASE_MIGRATION = ("card_reader_core", "0054_card_classification_final_state")
MANA_ROLE_MIGRATION = (
    "card_reader_core",
    "0055_seed_classification_rules_and_full_height_template",
)


def _migrate_to(target: tuple[str, str]) -> Any:
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def _create_card_version(
    apps: Any,
    *,
    key: str,
    card_pool: str,
    template: Any,
    lifecycle_status: str = "active",
    version_number: int = 1,
    is_latest: bool = True,
) -> tuple[Any, Any]:
    Card = apps.get_model("card_reader_core", "Card")
    CardVersion = apps.get_model("card_reader_core", "CardVersion")
    card, _created = Card.objects.get_or_create(
        key=key,
        card_pool=card_pool,
        faction_identity_key="[]",
        defaults={
            "label": key,
            "lifecycle_status": lifecycle_status,
        },
    )
    version = CardVersion.objects.create(
        card_id=card.id,
        template_id=template.id,
        version_number=version_number,
        image_hash=f"{key}-{version_number}",
        name=key,
        is_latest=is_latest,
    )
    if is_latest:
        card.latest_version_id = version.id
        card.save(update_fields=["latest_version"])
    return card, version


@pytest.mark.django_db(transaction=True)
def test_mana_role_migration_reuses_type_seeds_rules_and_backfills_latest_types() -> None:
    old_apps = _migrate_to(BASE_MIGRATION)
    CardClassificationRule = old_apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    CardRoleAssignment = old_apps.get_model("card_reader_core", "CardRoleAssignment")
    CardVersionType = old_apps.get_model("card_reader_core", "CardVersionType")
    Type = old_apps.get_model("card_reader_core", "Type")
    Template = old_apps.get_model("card_reader_core", "Template")

    CardClassificationRule.objects.filter(target_kind="role", target_key="mana").delete()
    CardRoleAssignment.objects.filter(role="mana").delete()
    Type.objects.filter(key="mana").delete()
    mana_type = Type.objects.create(
        key="mana",
        label="Existing Mana",
        identifiers_json=["existing mana"],
    )
    other_type = Type.objects.create(key="other-mana-migration", label="Other")
    template = Template.objects.create(
        key="mana-role-migration-template",
        label="Mana role migration template",
        definition_json={},
    )

    player, player_version = _create_card_version(
        old_apps,
        key="mana-migration-player",
        card_pool="player",
        template=template,
    )
    CardRoleAssignment.objects.create(card_id=player.id, role="hero")
    evil, evil_version = _create_card_version(
        old_apps,
        key="mana-migration-evil",
        card_pool="evil",
        template=template,
        lifecycle_status="deprecated",
    )
    neutral, neutral_version = _create_card_version(
        old_apps,
        key="mana-migration-neutral",
        card_pool="neutral",
        template=template,
    )
    old_only, old_version = _create_card_version(
        old_apps,
        key="mana-migration-old-only",
        card_pool="player",
        template=template,
        is_latest=False,
    )
    _old_only_card, latest_version = _create_card_version(
        old_apps,
        key="mana-migration-old-only",
        card_pool="player",
        template=template,
        version_number=2,
    )
    for version in (player_version, evil_version, neutral_version, old_version):
        CardVersionType.objects.create(card_version_id=version.id, type_id=mana_type.id)
    CardVersionType.objects.create(card_version_id=latest_version.id, type_id=other_type.id)

    apps = _migrate_to(MANA_ROLE_MIGRATION)
    MigratedRule = apps.get_model("card_reader_core", "CardClassificationRule")
    MigratedRole = apps.get_model("card_reader_core", "CardRoleAssignment")
    MigratedType = apps.get_model("card_reader_core", "Type")

    reused_type = MigratedType.objects.get(key="mana")
    assert reused_type.id == mana_type.id
    assert reused_type.label == "Existing Mana"
    assert reused_type.identifiers_json == ["existing mana"]
    assert set(
        MigratedRule.objects.filter(
            target_kind="role",
            target_key="mana",
            source_kind="type",
            type_id=mana_type.id,
        ).values_list("card_pool", "enabled")
    ) == {("player", True), ("evil", True)}
    assert set(
        MigratedRole.objects.filter(card_id=player.id).values_list("role", flat=True)
    ) == {"hero", "mana"}
    assert MigratedRole.objects.filter(card_id=evil.id, role="mana").exists()
    assert not MigratedRole.objects.filter(card_id=neutral.id, role="mana").exists()
    assert not MigratedRole.objects.filter(card_id=old_only.id, role="mana").exists()
    assert ("mana", "Mana") in MigratedRole._meta.get_field("role").choices

    reversed_apps = _migrate_to(BASE_MIGRATION)
    ReversedRule = reversed_apps.get_model("card_reader_core", "CardClassificationRule")
    ReversedRole = reversed_apps.get_model("card_reader_core", "CardRoleAssignment")
    assert not ReversedRule.objects.filter(
        target_kind="role",
        target_key="mana",
    ).exists()
    assert not ReversedRole.objects.filter(role="mana").exists()
    assert reversed_apps.get_model("card_reader_core", "Type").objects.filter(
        id=mana_type.id,
        label="Existing Mana",
    ).exists()

    reapplied_apps = _migrate_to(MANA_ROLE_MIGRATION)
    ReappliedRole = reapplied_apps.get_model("card_reader_core", "CardRoleAssignment")
    assert ReappliedRole.objects.filter(card_id=player.id, role="mana").count() == 1
    assert ReappliedRole.objects.filter(card_id=evil.id, role="mana").count() == 1
    _restore_leaf()


@pytest.mark.django_db(transaction=True)
def test_seed_reverse_preserves_custom_mana_classification() -> None:
    _migrate_to(BASE_MIGRATION)
    apps = _migrate_to(MANA_ROLE_MIGRATION)
    Card = apps.get_model("card_reader_core", "Card")
    CardClassificationRule = apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    Type = apps.get_model("card_reader_core", "Type")
    mana_type = Type.objects.get(key="mana")
    custom_card = Card.objects.create(
        key="custom-mana-role-migration",
        label="Custom Mana role migration",
        card_pool="neutral",
    )
    custom_assignment = CardRoleAssignment.objects.create(
        card_id=custom_card.id,
        role="mana",
    )
    custom_rule = CardClassificationRule.objects.create(
        card_pool="neutral",
        target_kind="role",
        target_key="mana",
        source_kind="type",
        type_id=mana_type.id,
        enabled=True,
    )

    reversed_apps = _migrate_to(BASE_MIGRATION)
    ReversedRule = reversed_apps.get_model("card_reader_core", "CardClassificationRule")
    ReversedRole = reversed_apps.get_model("card_reader_core", "CardRoleAssignment")
    assert ReversedRule.objects.filter(id=custom_rule.id).exists()
    assert ReversedRole.objects.filter(id=custom_assignment.id).exists()
    _restore_leaf()

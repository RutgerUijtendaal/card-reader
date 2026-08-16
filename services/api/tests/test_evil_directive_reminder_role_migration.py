from __future__ import annotations

from typing import Any

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest


BASE_MIGRATION = ("card_reader_core", "0059_add_mtg_like_mana_badge_ocr")
ROLE_MIGRATION = ("card_reader_core", "0060_add_evil_directive_reminder_roles")


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
        defaults={"label": key, "lifecycle_status": lifecycle_status},
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
def test_role_migration_creates_and_reuses_types_then_backfills_latest_evil_types() -> None:
    old_apps = _migrate_to(BASE_MIGRATION)
    OldRule = old_apps.get_model("card_reader_core", "CardClassificationRule")
    OldRole = old_apps.get_model("card_reader_core", "CardRoleAssignment")
    OldType = old_apps.get_model("card_reader_core", "Type")
    OldRule.objects.filter(target_kind="role", target_key__in=("directive", "reminder")).delete()
    OldRole.objects.filter(role__in=("directive", "reminder")).delete()
    OldType.objects.filter(key__in=("directive", "reminder")).delete()
    directive_type = OldType.objects.create(
        key="directive",
        label="Existing Directive",
        identifiers_json=["existing directive"],
    )

    seeded_apps = _migrate_to(ROLE_MIGRATION)
    SeededRule = seeded_apps.get_model("card_reader_core", "CardClassificationRule")
    SeededType = seeded_apps.get_model("card_reader_core", "Type")
    assert SeededType.objects.get(key="directive").id == directive_type.id
    assert SeededType.objects.get(key="directive").label == "Existing Directive"
    reminder_type = SeededType.objects.get(key="reminder")
    assert reminder_type.label == "Reminder"
    assert reminder_type.identifiers_json == ["reminder"]
    assert set(
        SeededRule.objects.filter(
            target_kind="role",
            target_key__in=("directive", "reminder"),
        ).values_list("card_pool", "target_key", "source_kind", "enabled")
    ) == {
        ("evil", "directive", "type", True),
        ("evil", "reminder", "type", True),
    }

    apps = _migrate_to(BASE_MIGRATION)
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    CardVersionType = apps.get_model("card_reader_core", "CardVersionType")
    Type = apps.get_model("card_reader_core", "Type")
    Template = apps.get_model("card_reader_core", "Template")
    directive_type = Type.objects.get(key="directive")
    reminder_type = Type.objects.get(key="reminder")
    other_type = Type.objects.create(key="directive-reminder-other", label="Other")
    template = Template.objects.create(
        key="directive-reminder-migration-template",
        label="Directive Reminder migration template",
        definition_json={},
    )

    evil_dual, evil_dual_version = _create_card_version(
        apps, key="directive-reminder-evil-dual", card_pool="evil", template=template
    )
    CardRoleAssignment.objects.create(card_id=evil_dual.id, role="boss")
    evil_deprecated, evil_deprecated_version = _create_card_version(
        apps,
        key="directive-reminder-evil-deprecated",
        card_pool="evil",
        template=template,
        lifecycle_status="deprecated",
    )
    player, player_version = _create_card_version(
        apps, key="directive-reminder-player", card_pool="player", template=template
    )
    neutral, neutral_version = _create_card_version(
        apps, key="directive-reminder-neutral", card_pool="neutral", template=template
    )
    old_only, old_version = _create_card_version(
        apps,
        key="directive-reminder-old-only",
        card_pool="evil",
        template=template,
        is_latest=False,
    )
    _old_only_card, latest_version = _create_card_version(
        apps,
        key="directive-reminder-old-only",
        card_pool="evil",
        template=template,
        version_number=2,
    )
    for version, type_rows in (
        (evil_dual_version, (directive_type, reminder_type)),
        (evil_deprecated_version, (reminder_type,)),
        (player_version, (directive_type, reminder_type)),
        (neutral_version, (directive_type, reminder_type)),
        (old_version, (directive_type, reminder_type)),
        (latest_version, (other_type,)),
    ):
        for type_row in type_rows:
            CardVersionType.objects.create(card_version_id=version.id, type_id=type_row.id)

    migrated_apps = _migrate_to(ROLE_MIGRATION)
    MigratedRole = migrated_apps.get_model("card_reader_core", "CardRoleAssignment")
    assert set(
        MigratedRole.objects.filter(card_id=evil_dual.id).values_list("role", flat=True)
    ) == {"boss", "directive", "reminder"}
    assert MigratedRole.objects.filter(card_id=evil_deprecated.id, role="reminder").exists()
    assert not MigratedRole.objects.filter(card_id=evil_deprecated.id, role="directive").exists()
    assert not MigratedRole.objects.filter(
        card_id__in=(player.id, neutral.id, old_only.id),
        role__in=("directive", "reminder"),
    ).exists()
    assert ("directive", "Directive") in MigratedRole._meta.get_field("role").choices
    assert ("reminder", "Reminder") in MigratedRole._meta.get_field("role").choices

    reversed_apps = _migrate_to(BASE_MIGRATION)
    ReversedRule = reversed_apps.get_model("card_reader_core", "CardClassificationRule")
    ReversedRole = reversed_apps.get_model("card_reader_core", "CardRoleAssignment")
    ReversedType = reversed_apps.get_model("card_reader_core", "Type")
    assert not ReversedRule.objects.filter(
        target_kind="role", target_key__in=("directive", "reminder")
    ).exists()
    assert not ReversedRole.objects.filter(role__in=("directive", "reminder")).exists()
    assert ReversedRole.objects.filter(card_id=evil_dual.id, role="boss").exists()
    assert ReversedType.objects.filter(id=directive_type.id, label="Existing Directive").exists()
    assert ReversedType.objects.filter(id=reminder_type.id, label="Reminder").exists()

    reapplied_apps = _migrate_to(ROLE_MIGRATION)
    ReappliedRole = reapplied_apps.get_model("card_reader_core", "CardRoleAssignment")
    assert ReappliedRole.objects.filter(card_id=evil_dual.id, role="directive").count() == 1
    assert ReappliedRole.objects.filter(card_id=evil_dual.id, role="reminder").count() == 1
    _restore_leaf()


@pytest.mark.django_db(transaction=True)
def test_role_migration_refuses_to_orphan_custom_assignments_and_rules() -> None:
    _migrate_to(BASE_MIGRATION)
    apps = _migrate_to(ROLE_MIGRATION)
    Card = apps.get_model("card_reader_core", "Card")
    CardClassificationRule = apps.get_model("card_reader_core", "CardClassificationRule")
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    Type = apps.get_model("card_reader_core", "Type")
    custom_card = Card.objects.create(
        key="custom-directive-reminder-migration",
        label="Custom Directive Reminder migration",
        card_pool="player",
    )
    custom_assignment = CardRoleAssignment.objects.create(card_id=custom_card.id, role="directive")
    custom_rule = CardClassificationRule.objects.create(
        card_pool="neutral",
        target_kind="role",
        target_key="reminder",
        source_kind="type",
        type_id=Type.objects.get(key="reminder").id,
        enabled=True,
    )

    with pytest.raises(RuntimeError, match="custom assignments or classification rules"):
        _migrate_to(BASE_MIGRATION)

    CardClassificationRule.objects.filter(id=custom_rule.id).delete()
    CardRoleAssignment.objects.filter(id=custom_assignment.id).delete()
    _migrate_to(BASE_MIGRATION)
    _restore_leaf()

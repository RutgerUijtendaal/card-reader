from __future__ import annotations

from django.apps.registry import Apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest


pytestmark = pytest.mark.migration_state

BASE_MIGRATION = (
    "card_reader_core",
    "0060_card_back_pool_defaults_and_overrides",
)
FIRE_MIGRATION = ("card_reader_core", "0061_fire_faction")


def _migrate_to(target: tuple[str, str]) -> Apps:
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_fire_faction_migration_reuses_the_tag_and_seeds_the_rule() -> None:
    old_apps = _migrate_to(BASE_MIGRATION)
    Tag = old_apps.get_model("card_reader_core", "Tag")
    existing_fire, _created = Tag.objects.get_or_create(
        key="fire",
        defaults={
            "label": "Fire",
            "identifiers_json": ["fire"],
        },
    )
    existing_fire.label = "Existing Fire"
    existing_fire.identifiers_json = ["flame"]
    existing_fire.save(update_fields=["label", "identifiers_json", "updated_at"])

    apps = _migrate_to(FIRE_MIGRATION)
    CardClassificationRule = apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    FireTag = apps.get_model("card_reader_core", "Tag")
    reused_fire = FireTag.objects.get(key="fire")
    assert reused_fire.id == existing_fire.id
    assert reused_fire.label == "Existing Fire"
    assert reused_fire.identifiers_json == ["flame"]
    assert CardClassificationRule.objects.filter(
        card_pool="evil",
        target_kind="faction",
        target_key="fire",
        source_kind="tag",
        tag_id=reused_fire.id,
        enabled=True,
    ).exists()

    reversed_apps = _migrate_to(BASE_MIGRATION)
    ReversedRule = reversed_apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    assert not ReversedRule.objects.filter(
        target_kind="faction",
        target_key="fire",
        source_kind="tag",
        tag__key="fire",
    ).exists()
    assert reversed_apps.get_model("card_reader_core", "Tag").objects.filter(
        id=existing_fire.id,
    ).exists()
    _restore_leaf()


@pytest.mark.django_db(transaction=True)
def test_fire_faction_reverse_preserves_a_staff_modified_seeded_rule() -> None:
    _migrate_to(BASE_MIGRATION)
    apps = _migrate_to(FIRE_MIGRATION)
    CardClassificationRule = apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    rule = CardClassificationRule.objects.get(
        card_pool="evil",
        target_kind="faction",
        target_key="fire",
        source_kind="tag",
        tag__key="fire",
    )
    rule.enabled = False
    rule.save(update_fields=["enabled", "updated_at"])

    reversed_apps = _migrate_to(BASE_MIGRATION)
    ReversedRule = reversed_apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    assert ReversedRule.objects.filter(id=rule.id, enabled=False).exists()
    ReversedRule.objects.filter(id=rule.id).delete()
    _restore_leaf()

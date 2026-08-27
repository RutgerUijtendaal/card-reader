from __future__ import annotations

from django.apps.registry import Apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
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
def test_fire_faction_reverse_rejects_a_staff_modified_seeded_rule() -> None:
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

    with pytest.raises(
        IrreversibleError,
        match="staff-modified or additional Fire classification rules",
    ):
        _migrate_to(BASE_MIGRATION)

    CardClassificationRule.objects.filter(id=rule.id).delete()
    _migrate_to(BASE_MIGRATION)
    _restore_leaf()


@pytest.mark.django_db(transaction=True)
def test_fire_faction_reverse_rejects_assignments_identities_and_snapshots() -> None:
    _migrate_to(BASE_MIGRATION)
    apps = _migrate_to(FIRE_MIGRATION)
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    CardClassificationReviewItem = apps.get_model(
        "card_reader_core",
        "CardClassificationReviewItem",
    )
    CardFactionAssignment = apps.get_model(
        "card_reader_core",
        "CardFactionAssignment",
    )
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")
    Template = apps.get_model("card_reader_core", "Template")

    card = Card.objects.create(
        key="fire-rollback-card",
        label="Fire Rollback Card",
        card_pool="evil",
        faction_identity_key='["fire"]',
    )
    CardFactionAssignment.objects.create(card_id=card.id, faction="fire")
    CardAlias.objects.create(
        card_id=card.id,
        key="fire-rollback-alias",
        label="Fire Rollback Alias",
        card_pool="evil",
        faction_identity_key='["fire"]',
    )
    template = Template.objects.create(
        key="fire-rollback-template",
        label="Fire Rollback Template",
    )
    job = ImportJob.objects.create(
        source_path="imports/fire-rollback",
        template_id=template.id,
        card_pool="evil",
        card_faction_override_json=["fire"],
        classification_rule_snapshot_json={
            "rules": [{"target_kind": "faction", "target_key": "fire"}],
        },
    )
    item = ImportJobItem.objects.create(
        job_id=job.id,
        source_file="fire-rollback.webp",
        resolved_card_factions_json=["fire"],
        classification_inference_json={"factions": {"resolved_factions": ["fire"]}},
        target_card_factions_snapshot_json=["fire"],
    )
    CardClassificationReviewItem.objects.create(
        import_item_id=item.id,
        card_id=card.id,
        card_pool="evil",
        existing_classification_json={"card_factions": ["fire"]},
        inferred_classification_json={"card_factions": ["fire"]},
        inference_evidence_json={"factions": {"resolved_factions": ["fire"]}},
    )

    with pytest.raises(IrreversibleError) as exception_info:
        _migrate_to(BASE_MIGRATION)

    message = str(exception_info.value)
    for blocker in (
        "card faction assignments",
        "card identity keys",
        "card alias identity keys",
        "ImportJob.card_faction_override_json",
        "ImportJob.classification_rule_snapshot_json",
        "ImportJobItem.resolved_card_factions_json",
        "ImportJobItem.classification_inference_json",
        "ImportJobItem.target_card_factions_snapshot_json",
        "CardClassificationReviewItem.existing_classification_json",
        "CardClassificationReviewItem.inferred_classification_json",
        "CardClassificationReviewItem.inference_evidence_json",
    ):
        assert blocker in message

    CardClassificationReviewItem.objects.filter(import_item_id=item.id).delete()
    ImportJobItem.objects.filter(id=item.id).delete()
    ImportJob.objects.filter(id=job.id).delete()
    Template.objects.filter(id=template.id).delete()
    CardAlias.objects.filter(card_id=card.id).delete()
    CardFactionAssignment.objects.filter(card_id=card.id).delete()
    Card.objects.filter(id=card.id).delete()
    _migrate_to(BASE_MIGRATION)
    _restore_leaf()

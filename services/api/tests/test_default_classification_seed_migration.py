from __future__ import annotations

from typing import Any

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest


BASE_MIGRATION = ("card_reader_core", "0054_card_classification_final_state")
SEED_MIGRATION = (
    "card_reader_core",
    "0055_seed_classification_rules_and_full_height_template",
)

EXPECTED_RULES = {
    ("player", "role", "hero", "type", "hero", True),
    ("evil", "role", "boss", "type", "boss", True),
    ("evil", "role", "location", "type", "location", True),
    ("evil", "faction", "order", "tag", "order", True),
    ("evil", "faction", "blood", "tag", "blood", True),
    ("evil", "faction", "dark", "tag", "dark", True),
    ("evil", "faction", "metal", "tag", "metal", True),
    ("neutral", "role", "boon", "type", "boon", True),
    ("neutral", "role", "event", "type", "event", True),
}


def _migrate_to(target: tuple[str, str]):
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def _rule_identities(CardClassificationRule: Any) -> set[tuple[object, ...]]:
    rows = CardClassificationRule.objects.select_related("tag", "type")
    return {
        (
            rule.card_pool,
            rule.target_kind,
            rule.target_key,
            rule.source_kind,
            rule.tag.key if rule.source_kind == "tag" else rule.type.key,
            rule.enabled,
        )
        for rule in rows
    }


@pytest.mark.django_db(transaction=True)
def test_seed_migration_reuses_sources_and_creates_missing_defaults() -> None:
    old_apps = _migrate_to(BASE_MIGRATION)
    CardClassificationRule = old_apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    Tag = old_apps.get_model("card_reader_core", "Tag")
    Template = old_apps.get_model("card_reader_core", "Template")
    Type = old_apps.get_model("card_reader_core", "Type")

    CardClassificationRule.objects.all().delete()
    Tag.objects.filter(key__in={"order", "blood", "dark", "metal"}).delete()
    Type.objects.filter(key__in={"hero", "boss", "boon", "event", "location"}).delete()
    Template.objects.filter(key="full-height").delete()
    existing_order = Tag.objects.create(
        key="order",
        label="Existing Order",
        identifiers_json=["existing order"],
    )

    apps = _migrate_to(SEED_MIGRATION)
    SeededRule = apps.get_model("card_reader_core", "CardClassificationRule")
    SeededTag = apps.get_model("card_reader_core", "Tag")
    SeededTemplate = apps.get_model("card_reader_core", "Template")
    SeededType = apps.get_model("card_reader_core", "Type")

    reused_order = SeededTag.objects.get(key="order")
    assert reused_order.id == existing_order.id
    assert reused_order.label == "Existing Order"
    assert reused_order.identifiers_json == ["existing order"]
    seeded_tag_keys = set(
        SeededTag.objects.filter(key__in={"order", "blood", "dark", "metal"}).values_list(
            "key",
            flat=True,
        )
    )
    assert seeded_tag_keys == {
        "order",
        "blood",
        "dark",
        "metal",
    }
    seeded_type_keys = set(
        SeededType.objects.filter(
            key__in={"hero", "boss", "boon", "event", "location"}
        ).values_list("key", flat=True)
    )
    assert seeded_type_keys == {
        "hero",
        "boss",
        "boon",
        "event",
        "location",
    }
    assert _rule_identities(SeededRule) == EXPECTED_RULES

    template = SeededTemplate.objects.get(key="full-height")
    assert template.label == "Full height"
    assert template.definition_json == {
        "id": "full-height",
        "version": 1,
        "regions": [
            {
                "region_id": "top_bar",
                "parser_type": "name",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.04,
                    "y": 0.02,
                    "w": 0.92,
                    "h": 0.07,
                },
                "ocr_config": {"ocr_min_confidence": 0.55},
            },
            {
                "region_id": "type_bar",
                "parser_type": "type_tag",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.05,
                    "y": 0.93,
                    "w": 0.9,
                    "h": 0.06,
                },
                "ocr_config": {},
            },
            {
                "region_id": "rules_text",
                "parser_type": "rules_text",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.05,
                    "y": 0.09,
                    "w": 0.9,
                    "h": 0.84,
                },
                "ocr_config": {},
            },
            {
                "region_id": "rules_text_fallback",
                "parser_type": "rules_text",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.05,
                    "y": 0.37,
                    "w": 0.9,
                    "h": 0.3,
                },
                "ocr_config": {},
            },
        ],
    }

    reversed_apps = _migrate_to(BASE_MIGRATION)
    ReversedRule = reversed_apps.get_model("card_reader_core", "CardClassificationRule")
    assert not ReversedRule.objects.exists()
    assert reversed_apps.get_model("card_reader_core", "Template").objects.filter(
        key="full-height"
    ).exists()

    reapplied_apps = _migrate_to(SEED_MIGRATION)
    ReappliedRule = reapplied_apps.get_model("card_reader_core", "CardClassificationRule")
    assert _rule_identities(ReappliedRule) == EXPECTED_RULES
    _restore_leaf()

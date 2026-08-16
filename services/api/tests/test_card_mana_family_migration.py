from __future__ import annotations

import hashlib
import json

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest


BASE_MIGRATION = ("card_reader_core", "0055_seed_classification_rules_and_full_height_template")
MANA_MIGRATION = ("card_reader_core", "0056_card_mana_families")


def _migrate_to(target: tuple[str, str]):
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_mana_migration_backfills_latest_player_symbols_and_seeds_available_rules() -> None:
    old_apps = _migrate_to(BASE_MIGRATION)
    Card = old_apps.get_model("card_reader_core", "Card")
    CardClassificationRule = old_apps.get_model(
        "card_reader_core", "CardClassificationRule"
    )
    CardVersion = old_apps.get_model("card_reader_core", "CardVersion")
    CardVersionSymbol = old_apps.get_model("card_reader_core", "CardVersionSymbol")
    Symbol = old_apps.get_model("card_reader_core", "Symbol")
    Template = old_apps.get_model("card_reader_core", "Template")
    ImportJob = old_apps.get_model("card_reader_core", "ImportJob")

    CardClassificationRule.objects.all().delete()
    CardVersionSymbol.objects.all().delete()
    CardVersion.objects.all().delete()
    Card.objects.all().delete()
    Symbol.objects.all().delete()
    Template.objects.all().delete()

    template = Template.objects.create(key="mana-migration", label="Mana Migration")
    symbols = {
        key: Symbol.objects.create(
            key=key,
            label=key.replace("-", " ").title(),
            symbol_type="mana",
            detector_type="template",
            detection_config_json={"threshold": 0.75},
            text_enrichment_json={"aliases": [key]},
            reference_assets_json=[f"symbols/{key}.webp"],
            text_token=f"{{{key}}}",
            enabled=True,
        )
        for key in (
            "arcane-mana",
            "dark-affinity",
            "primal-affinity",
            "primla-affinity",
            "colorless-mana-3",
            "unmatched-affinity",
        )
    }
    legacy_snapshot_body: dict[str, object] = {
        "schema_version": 1,
        "card_pool": "player",
        "rules": [],
    }
    legacy_snapshot = {
        **legacy_snapshot_body,
        "digest": hashlib.sha256(
            json.dumps(
                legacy_snapshot_body,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }
    queued_job = ImportJob.objects.create(
        source_path="imports/pre-mana-queued",
        template_id=template.id,
        card_pool="player",
        status="queued",
        classification_rule_snapshot_json=legacy_snapshot,
    )
    completed_job = ImportJob.objects.create(
        source_path="imports/pre-mana-completed",
        template_id=template.id,
        card_pool="player",
        status="completed",
        classification_rule_snapshot_json=legacy_snapshot,
    )

    def create_card(
        key: str,
        *,
        pool: str = "player",
        lifecycle_status: str = "active",
        latest_symbols: tuple[str, ...] | None,
        previous_symbols: tuple[str, ...] = (),
    ):
        card = Card.objects.create(
            key=key,
            label=key,
            card_pool=pool,
            lifecycle_status=lifecycle_status,
        )
        previous = CardVersion.objects.create(
            card_id=card.id,
            template_id=template.id,
            version_number=1,
            name=f"{key} previous",
            is_latest=latest_symbols is None,
        )
        for symbol_key in previous_symbols:
            CardVersionSymbol.objects.create(
                card_version_id=previous.id,
                symbol_id=symbols[symbol_key].id,
            )
        latest = previous
        if latest_symbols is not None:
            latest = CardVersion.objects.create(
                card_id=card.id,
                template_id=template.id,
                version_number=2,
                name=f"{key} latest",
                is_latest=True,
                previous_version_id=previous.id,
            )
            previous.is_latest = False
            previous.save(update_fields=["is_latest"])
            for symbol_key in latest_symbols:
                CardVersionSymbol.objects.create(
                    card_version_id=latest.id,
                    symbol_id=symbols[symbol_key].id,
                )
        card.latest_version_id = latest.id if latest_symbols is not None else None
        card.save(update_fields=["latest_version"])
        return card

    multicolor = create_card(
        "migration-multicolor",
        latest_symbols=("arcane-mana", "dark-affinity"),
        previous_symbols=("primal-affinity",),
    )
    deprecated = create_card(
        "migration-deprecated-primal",
        lifecycle_status="deprecated",
        latest_symbols=("primla-affinity",),
    )
    colorless = create_card(
        "migration-colorless",
        latest_symbols=("colorless-mana-3", "unmatched-affinity"),
    )
    missing_latest = create_card("migration-missing-latest", latest_symbols=None)
    evil = create_card(
        "migration-evil",
        pool="evil",
        latest_symbols=("arcane-mana",),
    )

    apps = _migrate_to(MANA_MIGRATION)
    MigratedCard = apps.get_model("card_reader_core", "Card")
    Assignment = apps.get_model("card_reader_core", "CardManaFamilyAssignment")
    Rule = apps.get_model("card_reader_core", "CardClassificationRule")
    MigratedVersion = apps.get_model("card_reader_core", "CardVersion")
    MigratedJob = apps.get_model("card_reader_core", "ImportJob")

    assert set(
        Assignment.objects.filter(card_id=multicolor.id).values_list(
            "mana_family", flat=True
        )
    ) == {"arcane", "dark"}
    assert MigratedCard.objects.get(id=multicolor.id).mana_family_sort_key == 6
    assert list(
        Assignment.objects.filter(card_id=deprecated.id).values_list(
            "mana_family", flat=True
        )
    ) == ["primal"]
    assert MigratedCard.objects.get(id=deprecated.id).mana_family_sort_key == 5
    for card in (colorless, missing_latest, evil):
        assert not Assignment.objects.filter(card_id=card.id).exists()
        assert MigratedCard.objects.get(id=card.id).mana_family_sort_key == 63

    assert set(
        Rule.objects.filter(target_kind="mana_family").values_list(
            "card_pool", "target_key", "source_kind", "symbol__key"
        )
    ) == {
        ("player", "arcane", "symbol", "arcane-mana"),
        ("player", "dark", "symbol", "dark-affinity"),
        ("player", "primal", "symbol", "primal-affinity"),
        ("player", "primal", "symbol", "primla-affinity"),
    }
    assert "mana_family_sort_key" not in {
        field.name for field in MigratedVersion._meta.get_fields()
    }
    queued_snapshot = MigratedJob.objects.get(
        id=queued_job.id
    ).classification_rule_snapshot_json
    assert queued_snapshot["schema_version"] == 3
    assert {
        (rule["target_key"], rule["source_key"])
        for rule in queued_snapshot["rules"]
        if rule["target_kind"] == "mana_family"
    } == {
        ("arcane", "arcane-mana"),
        ("dark", "dark-affinity"),
        ("primal", "primal-affinity"),
        ("primal", "primla-affinity"),
    }
    arcane_rule = next(
        rule
        for rule in queued_snapshot["rules"]
        if rule.get("source_key") == "arcane-mana"
    )
    assert arcane_rule["source_symbol"] == {
        "symbol_type": "mana",
        "detector_type": "template",
        "detection_config": {"threshold": 0.75},
        "text_enrichment": {"aliases": ["arcane-mana"]},
        "reference_assets": ["symbols/arcane-mana.webp"],
        "text_token": "{arcane-mana}",
        "enabled": True,
    }
    queued_body = {
        key: queued_snapshot[key]
        for key in ("schema_version", "card_pool", "rules")
    }
    assert queued_snapshot["digest"] == hashlib.sha256(
        json.dumps(queued_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert (
        MigratedJob.objects.get(id=completed_job.id).classification_rule_snapshot_json
        == legacy_snapshot
    )

    downgraded_apps = _migrate_to(BASE_MIGRATION)
    DowngradedRule = downgraded_apps.get_model(
        "card_reader_core", "CardClassificationRule"
    )
    assert not DowngradedRule.objects.filter(source_kind="symbol").exists()

    _restore_leaf()

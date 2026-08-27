from __future__ import annotations

from uuid import UUID, uuid5

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.exceptions import IrreversibleError


MIGRATION_DEFAULT_NAMESPACE = UUID("d5050158-0d5c-419c-9506-e704938447c9")
FIRE_RULE = ("evil", "faction", "fire", "tag", "fire")
FIRE_IDENTITY_FRAGMENT = '"fire"'
FIRE_JSON_FIELDS = (
    (
        "ImportJob",
        (
            "card_faction_override_json",
            "classification_rule_snapshot_json",
        ),
    ),
    (
        "ImportJobItem",
        (
            "resolved_card_factions_json",
            "classification_inference_json",
            "target_card_factions_snapshot_json",
        ),
    ),
    (
        "CardClassificationReviewItem",
        (
            "existing_classification_json",
            "inferred_classification_json",
            "inference_evidence_json",
        ),
    ),
)


def _migration_default_id(kind: str, identity: str) -> str:
    return str(uuid5(MIGRATION_DEFAULT_NAMESPACE, f"{kind}:{identity}"))


def _classification_rule_id(rule: tuple[str, str, str, str, str]) -> str:
    return _migration_default_id("classification-rule", ":".join(rule))


def _json_value_contains_fire(value: object) -> bool:
    if value == "fire":
        return True
    if isinstance(value, list):
        for item in value:
            if _json_value_contains_fire(item):
                return True
        return False
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "fire" or _json_value_contains_fire(item):
                return True
    return False


def _json_field_contains_fire(
    apps: Apps,
    model_name: str,
    field_name: str,
) -> bool:
    model = apps.get_model("card_reader_core", model_name)
    values = model.objects.values_list(field_name, flat=True).iterator(chunk_size=1000)
    for value in values:
        if _json_value_contains_fire(value):
            return True
    return False


def _fire_rollback_blockers(apps: Apps) -> list[str]:
    blockers: list[str] = []

    CardFactionAssignment = apps.get_model(
        "card_reader_core",
        "CardFactionAssignment",
    )
    if CardFactionAssignment.objects.filter(faction="fire").exists():
        blockers.append("card faction assignments")

    for model_name, label in (
        ("Card", "card identity keys"),
        ("CardAlias", "card alias identity keys"),
    ):
        model = apps.get_model("card_reader_core", model_name)
        if model.objects.filter(
            faction_identity_key__contains=FIRE_IDENTITY_FRAGMENT,
        ).exists():
            blockers.append(label)

    for model_name, field_names in FIRE_JSON_FIELDS:
        for field_name in field_names:
            if _json_field_contains_fire(apps, model_name, field_name):
                blockers.append(f"{model_name}.{field_name}")

    CardClassificationRule = apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    fire_rules = CardClassificationRule.objects.filter(
        target_kind="faction",
        target_key="fire",
    )
    removable_seeded_rule = fire_rules.filter(
        id=_classification_rule_id(FIRE_RULE),
        card_pool="evil",
        source_kind="tag",
        tag__key="fire",
        type_id=None,
        symbol_id=None,
        enabled=True,
    )
    removable_rule_count = 1 if removable_seeded_rule.exists() else 0
    if fire_rules.count() != removable_rule_count:
        blockers.append("staff-modified or additional Fire classification rules")

    return blockers


def seed_fire_faction_rule(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    Tag = apps.get_model("card_reader_core", "Tag")
    fire_tag, _created = Tag.objects.get_or_create(
        key="fire",
        defaults={
            "id": _migration_default_id("tag", "fire"),
            "label": "Fire",
            "identifiers_json": ["fire"],
        },
    )

    CardClassificationRule = apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    CardClassificationRule.objects.get_or_create(
        card_pool="evil",
        target_kind="faction",
        target_key="fire",
        source_kind="tag",
        tag_id=fire_tag.id,
        type_id=None,
        symbol_id=None,
        defaults={
            "id": _classification_rule_id(FIRE_RULE),
            "enabled": True,
        },
    )


def remove_seeded_fire_faction_rule(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    blockers = _fire_rollback_blockers(apps)
    if blockers:
        blocker_list = ", ".join(blockers)
        raise IrreversibleError(
            "Cannot reverse 0061_fire_faction while Fire classification data exists: "
            f"{blocker_list}. Remove or migrate that data before retrying."
        )

    CardClassificationRule = apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    CardClassificationRule.objects.filter(
        id=_classification_rule_id(FIRE_RULE),
        card_pool="evil",
        target_kind="faction",
        target_key="fire",
        source_kind="tag",
        tag__key="fire",
        type_id=None,
        symbol_id=None,
        enabled=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0060_card_back_pool_defaults_and_overrides")]

    operations = [
        migrations.AlterField(
            model_name="cardfactionassignment",
            name="faction",
            field=models.CharField(
                choices=[
                    ("order", "Order"),
                    ("blood", "Blood"),
                    ("dark", "Dark"),
                    ("metal", "Metal"),
                    ("fire", "Fire"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
        migrations.RunPython(
            seed_fire_faction_rule,
            remove_seeded_fire_faction_rule,
        ),
    ]

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID, uuid5

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


MIGRATION_DEFAULT_NAMESPACE = UUID("d5050158-0d5c-419c-9506-e704938447c9")

SOURCE_DEFINITIONS = {
    "tag": (
        ("order", "Order", ["order"]),
        ("blood", "Blood", ["blood"]),
        ("dark", "Dark", ["dark"]),
        ("metal", "Metal", ["metal"]),
    ),
    "type": (
        ("hero", "Hero", ["hero"]),
        ("boss", "Boss", ["boss"]),
        ("boon", "Boon", ["boon"]),
        ("event", "Event", ["event"]),
        ("location", "Location", ["location"]),
        ("mana", "Mana", ["mana"]),
        ("directive", "Directive", ["directive"]),
        ("reminder", "Reminder", ["reminder"]),
    ),
}

CLASSIFICATION_RULES = (
    ("player", "role", "hero", "type", "hero"),
    ("player", "role", "mana", "type", "mana"),
    ("evil", "role", "boss", "type", "boss"),
    ("evil", "role", "location", "type", "location"),
    ("evil", "role", "mana", "type", "mana"),
    ("evil", "role", "directive", "type", "directive"),
    ("evil", "role", "reminder", "type", "reminder"),
    ("evil", "faction", "order", "tag", "order"),
    ("evil", "faction", "blood", "tag", "blood"),
    ("evil", "faction", "dark", "tag", "dark"),
    ("evil", "faction", "metal", "tag", "metal"),
    ("neutral", "role", "boon", "type", "boon"),
    ("neutral", "role", "event", "type", "event"),
)

ROLE_BACKFILL_POOLS = {
    "mana": ("player", "evil"),
    "directive": ("evil",),
    "reminder": ("evil",),
}

MTG_LIKE_V1_NAME_REGION_CUT = {
    "unit": "relative",
    "x": 0.04,
    "y": 0.02,
    "w": 0.92,
    "h": 0.07,
}
MTG_LIKE_V1_MANA_BADGE_OCR = {
    "cut_region": {
        "unit": "relative",
        "x": 0.86,
        "y": 0.0,
        "w": 0.14,
        "h": 1.0,
    },
    "scales": [3, 2],
}

FULL_HEIGHT_TEMPLATE_DEFINITION: dict[str, Any] = {
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


def _migration_default_id(kind: str, identity: str) -> str:
    return str(uuid5(MIGRATION_DEFAULT_NAMESPACE, f"{kind}:{identity}"))


def _classification_rule_id(rule: tuple[str, str, str, str, str]) -> str:
    return _migration_default_id("classification-rule", ":".join(rule))


def _role_assignment_id(card_id: str, role: str) -> str:
    return _migration_default_id("card-role-assignment", f"{card_id}:{role}")


def _source_models(apps: Apps) -> dict[str, Any]:
    return {
        "tag": apps.get_model("card_reader_core", "Tag"),
        "type": apps.get_model("card_reader_core", "Type"),
    }


def seed_classification_rules_and_template(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    source_models = _source_models(apps)
    sources: dict[tuple[str, str], Any] = {}
    for source_kind, definitions in SOURCE_DEFINITIONS.items():
        source_model = source_models[source_kind]
        for key, label, identifiers in definitions:
            source, _created = source_model.objects.get_or_create(
                key=key,
                defaults={
                    "id": _migration_default_id(source_kind, key),
                    "label": label,
                    "identifiers_json": identifiers,
                },
            )
            sources[(source_kind, key)] = source

    Template = apps.get_model("card_reader_core", "Template")
    Template.objects.get_or_create(
        key="full-height",
        defaults={
            "id": _migration_default_id("template", "full-height"),
            "label": "Full height",
            "definition_json": FULL_HEIGHT_TEMPLATE_DEFINITION,
        },
    )

    CardClassificationRule = apps.get_model("card_reader_core", "CardClassificationRule")
    for rule_definition in CLASSIFICATION_RULES:
        card_pool, target_kind, target_key, source_kind, source_key = rule_definition
        source = sources[(source_kind, source_key)]
        source_fields = (
            {"tag_id": source.id, "type_id": None}
            if source_kind == "tag"
            else {"tag_id": None, "type_id": source.id}
        )
        CardClassificationRule.objects.get_or_create(
            card_pool=card_pool,
            target_kind=target_kind,
            target_key=target_key,
            source_kind=source_kind,
            **source_fields,
            defaults={
                "id": _classification_rule_id(rule_definition),
                "enabled": True,
            },
        )

    Card = apps.get_model("card_reader_core", "Card")
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    for role, pools in ROLE_BACKFILL_POOLS.items():
        source = sources[("type", role)]
        card_ids = list(
            Card.objects.filter(
                card_pool__in=pools,
                latest_version__card_version_types__type_id=source.id,
            )
            .order_by("id")
            .values_list("id", flat=True)
        )
        existing_card_ids = set(
            CardRoleAssignment.objects.filter(
                card_id__in=card_ids,
                role=role,
            ).values_list("card_id", flat=True)
        )
        CardRoleAssignment.objects.bulk_create(
            [
                CardRoleAssignment(
                    id=_role_assignment_id(str(card_id), role),
                    card_id=card_id,
                    role=role,
                )
                for card_id in card_ids
                if card_id not in existing_card_ids
            ],
            batch_size=1000,
        )


def add_mtg_like_mana_badge_ocr(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    Template = apps.get_model("card_reader_core", "Template")
    template = Template.objects.filter(key="mtg-like-v1").first()
    if template is None or not isinstance(template.definition_json, dict):
        return

    definition: dict[str, Any] = deepcopy(template.definition_json)
    regions = definition.get("regions")
    if not isinstance(regions, list):
        return

    for region in regions:
        if not isinstance(region, dict):
            continue
        if region.get("parser_type") != "name_mana_cost":
            continue
        if region.get("cut_region") != MTG_LIKE_V1_NAME_REGION_CUT:
            continue
        if "mana_badge_ocr" in region:
            return
        region["mana_badge_ocr"] = deepcopy(MTG_LIKE_V1_MANA_BADGE_OCR)
        template.definition_json = definition
        template.save(update_fields=["definition_json", "updated_at"])
        return


def remove_seeded_classification_rules(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    CardClassificationRule = apps.get_model("card_reader_core", "CardClassificationRule")
    for rule_definition in CLASSIFICATION_RULES:
        card_pool, target_kind, target_key, source_kind, source_key = rule_definition
        source_fields = (
            {"tag__key": source_key, "type_id": None}
            if source_kind == "tag"
            else {"tag_id": None, "type__key": source_key}
        )
        CardClassificationRule.objects.filter(
            id=_classification_rule_id(rule_definition),
            card_pool=card_pool,
            target_kind=target_kind,
            target_key=target_key,
            source_kind=source_kind,
            enabled=True,
            **source_fields,
        ).delete()

    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    migration_assignment_ids = [
        assignment_id
        for assignment_id, card_id, role in CardRoleAssignment.objects.filter(
            role__in=tuple(ROLE_BACKFILL_POOLS),
        ).values_list("id", "card_id", "role")
        if assignment_id == _role_assignment_id(str(card_id), role)
    ]
    CardRoleAssignment.objects.filter(id__in=migration_assignment_ids).delete()


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0054_card_classification_final_state")]

    operations = [
        migrations.RunPython(
            seed_classification_rules_and_template,
            remove_seeded_classification_rules,
        ),
        migrations.RunPython(add_mtg_like_mana_badge_ocr, migrations.RunPython.noop),
    ]

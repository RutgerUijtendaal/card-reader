from __future__ import annotations

from uuid import UUID, uuid5

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


MIGRATION_DEFAULT_NAMESPACE = UUID("d5050158-0d5c-419c-9506-e704938447c9")
ROLE_TYPE_DEFINITIONS = (
    ("directive", "Directive"),
    ("reminder", "Reminder"),
)
ROLE_KEYS = tuple(key for key, _label in ROLE_TYPE_DEFINITIONS)
RULE_DEFINITIONS = tuple(("evil", "role", key, "type", key) for key in ROLE_KEYS)
ROLE_CHOICES = [
    ("hero", "Hero"),
    ("boss", "Boss"),
    ("location", "Location"),
    ("boon", "Boon"),
    ("event", "Event"),
    ("shop_item", "Shop Item"),
    ("directive", "Directive"),
    ("reminder", "Reminder"),
    ("mana", "Mana"),
]


def _migration_default_id(kind: str, identity: str) -> str:
    return str(uuid5(MIGRATION_DEFAULT_NAMESPACE, f"{kind}:{identity}"))


def _classification_rule_id(rule: tuple[str, str, str, str, str]) -> str:
    return _migration_default_id("classification-rule", ":".join(rule))


def _role_assignment_id(card_id: str, role: str) -> str:
    return _migration_default_id("card-role-assignment", f"{card_id}:{role}")


def add_evil_directive_reminder_defaults_and_backfill(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    CardClassificationRule = apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    Type = apps.get_model("card_reader_core", "Type")

    types = {}
    for key, label in ROLE_TYPE_DEFINITIONS:
        type_row, _created = Type.objects.get_or_create(
            key=key,
            defaults={
                "id": _migration_default_id("type", key),
                "label": label,
                "identifiers_json": [key],
            },
        )
        types[key] = type_row

    for rule_definition in RULE_DEFINITIONS:
        card_pool, target_kind, target_key, source_kind, source_key = rule_definition
        CardClassificationRule.objects.get_or_create(
            card_pool=card_pool,
            target_kind=target_kind,
            target_key=target_key,
            source_kind=source_kind,
            tag_id=None,
            type_id=types[source_key].id,
            symbol_id=None,
            defaults={
                "id": _classification_rule_id(rule_definition),
                "enabled": True,
            },
        )

    for role, _label in ROLE_TYPE_DEFINITIONS:
        card_ids = list(
            Card.objects.filter(
                card_pool="evil",
                latest_version__card_version_types__type_id=types[role].id,
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


def remove_evil_directive_reminder_defaults_and_backfill(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    CardClassificationRule = apps.get_model(
        "card_reader_core",
        "CardClassificationRule",
    )
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    Type = apps.get_model("card_reader_core", "Type")

    migration_assignment_ids = [
        assignment_id
        for assignment_id, card_id, role in CardRoleAssignment.objects.filter(
            role__in=ROLE_KEYS,
        ).values_list("id", "card_id", "role")
        if assignment_id == _role_assignment_id(str(card_id), role)
    ]
    CardRoleAssignment.objects.filter(id__in=migration_assignment_ids).delete()

    for rule_definition in RULE_DEFINITIONS:
        card_pool, target_kind, target_key, source_kind, source_key = rule_definition
        type_row = Type.objects.filter(key=source_key).first()
        if type_row is None:
            continue
        CardClassificationRule.objects.filter(
            id=_classification_rule_id(rule_definition),
            card_pool=card_pool,
            target_kind=target_kind,
            target_key=target_key,
            source_kind=source_kind,
            tag_id=None,
            type_id=type_row.id,
            symbol_id=None,
            enabled=True,
        ).delete()

    unsafe_assignments = CardRoleAssignment.objects.filter(role__in=ROLE_KEYS).exists()
    unsafe_rules = CardClassificationRule.objects.filter(
        target_kind="role",
        target_key__in=ROLE_KEYS,
    ).exists()
    if unsafe_assignments or unsafe_rules:
        raise RuntimeError(
            "Cannot remove the Directive and Reminder roles while custom assignments or "
            "classification rules exist."
        )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0059_add_mtg_like_mana_badge_ocr")]

    operations = [
        migrations.AlterField(
            model_name="cardroleassignment",
            name="role",
            field=models.CharField(
                choices=ROLE_CHOICES,
                db_index=True,
                max_length=64,
            ),
        ),
        migrations.RunPython(
            add_evil_directive_reminder_defaults_and_backfill,
            remove_evil_directive_reminder_defaults_and_backfill,
        ),
    ]

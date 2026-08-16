from __future__ import annotations

from uuid import UUID, uuid5

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


MIGRATION_DEFAULT_NAMESPACE = UUID("d5050158-0d5c-419c-9506-e704938447c9")
MANA_TYPE_KEY = "mana"
MANA_ROLE = "mana"
MANA_RULE_DEFINITIONS = (
    ("player", "role", MANA_ROLE, "type", MANA_TYPE_KEY),
    ("evil", "role", MANA_ROLE, "type", MANA_TYPE_KEY),
)
MANA_ROLE_CHOICES = [
    ("hero", "Hero"),
    ("boss", "Boss"),
    ("location", "Location"),
    ("boon", "Boon"),
    ("event", "Event"),
    ("shop_item", "Shop Item"),
    (MANA_ROLE, "Mana"),
]


def _migration_default_id(kind: str, identity: str) -> str:
    return str(uuid5(MIGRATION_DEFAULT_NAMESPACE, f"{kind}:{identity}"))


def _classification_rule_id(rule: tuple[str, str, str, str, str]) -> str:
    return _migration_default_id("classification-rule", ":".join(rule))


def _mana_role_assignment_id(card_id: str) -> str:
    return _migration_default_id("card-role-assignment", f"{card_id}:{MANA_ROLE}")


def add_mana_role_defaults_and_backfill(
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

    mana_type, _created = Type.objects.get_or_create(
        key=MANA_TYPE_KEY,
        defaults={
            "id": _migration_default_id("type", MANA_TYPE_KEY),
            "label": "Mana",
            "identifiers_json": [MANA_TYPE_KEY],
        },
    )
    for rule_definition in MANA_RULE_DEFINITIONS:
        card_pool, target_kind, target_key, source_kind, _source_key = rule_definition
        CardClassificationRule.objects.get_or_create(
            card_pool=card_pool,
            target_kind=target_kind,
            target_key=target_key,
            source_kind=source_kind,
            tag_id=None,
            type_id=mana_type.id,
            symbol_id=None,
            defaults={
                "id": _classification_rule_id(rule_definition),
                "enabled": True,
            },
        )

    card_ids = list(
        Card.objects.filter(
            card_pool__in=("player", "evil"),
            latest_version__card_version_types__type_id=mana_type.id,
        )
        .order_by("id")
        .values_list("id", flat=True)
    )
    existing_card_ids = set(
        CardRoleAssignment.objects.filter(
            card_id__in=card_ids,
            role=MANA_ROLE,
        ).values_list("card_id", flat=True)
    )
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(
                id=_mana_role_assignment_id(str(card_id)),
                card_id=card_id,
                role=MANA_ROLE,
            )
            for card_id in card_ids
            if card_id not in existing_card_ids
        ],
        batch_size=1000,
    )


def remove_mana_role_defaults_and_backfill(
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
        for assignment_id, card_id in CardRoleAssignment.objects.filter(
            role=MANA_ROLE,
        ).values_list("id", "card_id")
        if assignment_id == _mana_role_assignment_id(str(card_id))
    ]
    CardRoleAssignment.objects.filter(id__in=migration_assignment_ids).delete()

    mana_type = Type.objects.filter(key=MANA_TYPE_KEY).first()
    if mana_type is not None:
        for rule_definition in MANA_RULE_DEFINITIONS:
            card_pool, target_kind, target_key, source_kind, _source_key = rule_definition
            CardClassificationRule.objects.filter(
                id=_classification_rule_id(rule_definition),
                card_pool=card_pool,
                target_kind=target_kind,
                target_key=target_key,
                source_kind=source_kind,
                tag_id=None,
                type_id=mana_type.id,
                symbol_id=None,
                enabled=True,
            ).delete()

    unsafe_assignments = CardRoleAssignment.objects.filter(role=MANA_ROLE).exists()
    unsafe_rules = CardClassificationRule.objects.filter(
        target_kind="role",
        target_key=MANA_ROLE,
    ).exists()
    if unsafe_assignments or unsafe_rules:
        raise RuntimeError(
            "Cannot remove the Mana role while custom Mana assignments or classification rules exist."
        )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0057_card_classification_review_item")]

    operations = [
        migrations.AlterField(
            model_name="cardroleassignment",
            name="role",
            field=models.CharField(
                choices=MANA_ROLE_CHOICES,
                db_index=True,
                max_length=64,
            ),
        ),
        migrations.RunPython(
            add_mana_role_defaults_and_backfill,
            remove_mana_role_defaults_and_backfill,
        ),
    ]

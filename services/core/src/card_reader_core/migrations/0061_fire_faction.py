from __future__ import annotations

from uuid import UUID, uuid5

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


MIGRATION_DEFAULT_NAMESPACE = UUID("d5050158-0d5c-419c-9506-e704938447c9")
FIRE_RULE = ("evil", "faction", "fire", "tag", "fire")


def _migration_default_id(kind: str, identity: str) -> str:
    return str(uuid5(MIGRATION_DEFAULT_NAMESPACE, f"{kind}:{identity}"))


def _classification_rule_id(rule: tuple[str, str, str, str, str]) -> str:
    return _migration_default_id("classification-rule", ":".join(rule))


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

from __future__ import annotations

from typing import Any
from uuid import uuid4

import card_reader_core.models.base
import django.db.models.deletion
from django.db import migrations, models


CARD_POOL_CHOICES = [("player", "Player"), ("evil", "Evil"), ("neutral", "Neutral")]
CARD_ROLE_CHOICES = [
    ("hero", "Hero"),
    ("boss", "Boss"),
    ("location", "Location"),
    ("boon", "Boon"),
    ("event", "Event"),
    ("shop_item", "Shop Item"),
]
CARD_FACTION_CHOICES = [
    ("order", "Order"),
    ("blood", "Blood"),
    ("dark", "Dark"),
    ("metal", "Metal"),
]
EMPTY_FACTION_IDENTITY_KEY = "[]"


def populate_master_data(apps: Any, _schema_editor: Any) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    CardIdentityPoolLock = apps.get_model("card_reader_core", "CardIdentityPoolLock")
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")

    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card_id=card_id, role="hero")
            for card_id in Card.objects.filter(is_hero=True).values_list("id", flat=True).iterator()
        ],
        ignore_conflicts=True,
    )

    for alias in CardAlias.objects.select_related("card").iterator():
        alias.card_pool = alias.card.card_pool
        alias.faction_identity_key = alias.card.faction_identity_key
        alias.save(update_fields=["card_pool", "faction_identity_key"])

    for alias in CardAlias.objects.iterator():
        collision = (
            Card.objects.filter(
                card_pool=alias.card_pool,
                faction_identity_key=alias.faction_identity_key,
                key=alias.key,
            )
            .exclude(id=alias.card_id)
            .exists()
        )
        if collision:
            raise RuntimeError(
                "Cannot establish card identity namespaces while a primary card key also exists "
                f"as another card's alias: '{alias.key}'. Resolve the collision before retrying."
            )

    for job in ImportJob.objects.iterator():
        job.creation_key = str(uuid4())
        job.save(update_fields=["creation_key"])

    for item in ImportJobItem.objects.iterator():
        if item.warning_code or item.warning_message:
            item.warnings_json = [
                {
                    "code": item.warning_code or "legacy_import_warning",
                    "message": item.warning_message or "Import completed with a warning.",
                }
            ]
            item.save(update_fields=["warnings_json"])

    CardIdentityPoolLock.objects.bulk_create(
        [CardIdentityPoolLock(card_pool=card_pool) for card_pool, _label in CARD_POOL_CHOICES]
    )


def restore_master_hero_flags(apps: Any, _schema_editor: Any) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    CardRoleAssignment = apps.get_model("card_reader_core", "CardRoleAssignment")
    hero_card_ids = CardRoleAssignment.objects.filter(role="hero").values_list(
        "card_id", flat=True
    )
    Card.objects.update(is_hero=False)
    Card.objects.filter(id__in=hero_card_ids).update(is_hero=True)


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0053_deck_creation")]

    operations = [
        migrations.CreateModel(
            name="CardClassificationRule",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                (
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "card_pool",
                    models.CharField(choices=CARD_POOL_CHOICES, db_index=True, max_length=16),
                ),
                (
                    "target_kind",
                    models.CharField(
                        choices=[("role", "Role"), ("faction", "Faction")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                ("target_key", models.CharField(db_index=True, max_length=64)),
                (
                    "source_kind",
                    models.CharField(
                        choices=[("tag", "Tag"), ("type", "Type")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                ("enabled", models.BooleanField(db_index=True, default=True)),
                (
                    "tag",
                    models.ForeignKey(
                        blank=True,
                        db_column="tag_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="classification_rules",
                        to="card_reader_core.tag",
                    ),
                ),
                (
                    "type",
                    models.ForeignKey(
                        blank=True,
                        db_column="type_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="classification_rules",
                        to="card_reader_core.type",
                    ),
                ),
            ],
            options={
                "db_table": "card_classification_rule",
                "indexes": [
                    models.Index(
                        fields=["card_pool", "enabled", "tag"],
                        name="ix_class_rule_pool_tag",
                    ),
                    models.Index(
                        fields=["card_pool", "enabled", "type"],
                        name="ix_class_rule_pool_type",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                source_kind="tag",
                                tag__isnull=False,
                                type__isnull=True,
                            )
                            | models.Q(
                                source_kind="type",
                                tag__isnull=True,
                                type__isnull=False,
                            )
                        ),
                        name="ck_classification_rule_source_fk",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(source_kind="tag"),
                        fields=("card_pool", "target_kind", "target_key", "tag"),
                        name="uq_class_rule_tag_target",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(source_kind="type"),
                        fields=("card_pool", "target_kind", "target_key", "type"),
                        name="uq_class_rule_type_target",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="CardFactionAssignment",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                (
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "faction",
                    models.CharField(choices=CARD_FACTION_CHOICES, db_index=True, max_length=64),
                ),
                (
                    "card",
                    models.ForeignKey(
                        db_column="card_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="faction_assignments",
                        to="card_reader_core.card",
                    ),
                ),
            ],
            options={
                "db_table": "card_faction_assignment",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("card", "faction"),
                        name="uq_card_faction_assignment_card_faction",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CardIdentityPoolLock",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                (
                    "card_pool",
                    models.CharField(
                        choices=CARD_POOL_CHOICES,
                        max_length=16,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("revision", models.PositiveBigIntegerField(default=0)),
            ],
            options={"db_table": "card_identity_pool_lock"},
        ),
        migrations.CreateModel(
            name="CardRoleAssignment",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                (
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "role",
                    models.CharField(choices=CARD_ROLE_CHOICES, db_index=True, max_length=64),
                ),
                (
                    "card",
                    models.ForeignKey(
                        db_column="card_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to="card_reader_core.card",
                    ),
                ),
            ],
            options={
                "db_table": "card_role_assignment",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("card", "role"),
                        name="uq_card_role_assignment_card_role",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="card",
            name="card_pool",
            field=models.CharField(
                choices=CARD_POOL_CHOICES,
                db_index=True,
                default="player",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="faction_identity_key",
            field=models.TextField(default=EMPTY_FACTION_IDENTITY_KEY, editable=False),
        ),
        migrations.AddField(
            model_name="cardalias",
            name="card_pool",
            field=models.CharField(
                blank=True,
                choices=CARD_POOL_CHOICES,
                db_index=True,
                max_length=16,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="cardalias",
            name="faction_identity_key",
            field=models.TextField(default=EMPTY_FACTION_IDENTITY_KEY, editable=False),
        ),
        migrations.AddField(
            model_name="importjob",
            name="card_faction_mode",
            field=models.TextField(default="automatic"),
        ),
        migrations.AddField(
            model_name="importjob",
            name="card_faction_override_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjob",
            name="card_pool",
            field=models.TextField(default="player"),
        ),
        migrations.AddField(
            model_name="importjob",
            name="card_role_mode",
            field=models.TextField(default="automatic"),
        ),
        migrations.AddField(
            model_name="importjob",
            name="card_role_override_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjob",
            name="classification_rule_snapshot_json",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="importjob",
            name="creation_fingerprint",
            field=models.TextField(default=""),
        ),
        migrations.AddField(
            model_name="importjob",
            name="creation_key",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="classification_inference_json",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="resolved_card_factions_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="resolved_card_roles_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="target_card_factions_snapshot_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="target_card_pool_snapshot",
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="target_card_roles_snapshot_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="warnings_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="ttscardsheet",
            name="card_pool",
            field=models.CharField(
                choices=CARD_POOL_CHOICES,
                db_index=True,
                default="player",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="ttscardsheetslot",
            name="card_pool",
            field=models.CharField(
                choices=CARD_POOL_CHOICES,
                db_index=True,
                default="player",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="key",
            field=models.TextField(db_index=True, default=""),
        ),
        migrations.AlterField(
            model_name="cardalias",
            name="key",
            field=models.TextField(db_index=True, default=""),
        ),
        migrations.AlterField(
            model_name="cardback",
            name="stored_path",
            field=models.TextField(db_index=True),
        ),
        migrations.AlterField(
            model_name="cardversionimage",
            name="stored_path",
            field=models.TextField(db_index=True),
        ),
        migrations.AlterField(
            model_name="ttscardsheetslot",
            name="card_identity_id",
            field=models.TextField(db_index=True),
        ),
        migrations.RenameIndex(
            model_name="cardgroupmember",
            old_name="ix_card_group_member_card_position",
            new_name="ix_card_group_card_pos",
        ),
        migrations.RenameIndex(
            model_name="cardversionparseflagitem",
            old_name="ix_parse_flag_item_status_created",
            new_name="ix_parse_flag_status_created",
        ),
        migrations.RenameIndex(
            model_name="decksideboardentry",
            old_name="ix_deck_sideboard_entry_created",
            new_name="ix_sideboard_entry_created",
        ),
        migrations.RenameIndex(
            model_name="useraccessrequest",
            old_name="ix_access_request_contact_status",
            new_name="ix_access_contact_status",
        ),
        migrations.RenameIndex(
            model_name="usernotification",
            old_name="ix_notification_recipient_dedupe",
            new_name="ix_notif_recipient_dedupe",
        ),
        migrations.RunPython(populate_master_data, restore_master_hero_flags),
        migrations.AlterField(
            model_name="cardalias",
            name="card_pool",
            field=models.CharField(choices=CARD_POOL_CHOICES, db_index=True, max_length=16),
        ),
        migrations.AlterField(
            model_name="importjob",
            name="creation_key",
            field=models.TextField(default=card_reader_core.models.base.uuid_str, unique=True),
        ),
        migrations.AddConstraint(
            model_name="card",
            constraint=models.UniqueConstraint(
                fields=("card_pool", "faction_identity_key", "key"),
                name="uq_card_pool_faction_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardalias",
            constraint=models.UniqueConstraint(
                fields=("card_pool", "faction_identity_key", "key"),
                name="uq_card_alias_pool_faction_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="ttscardsheetslot",
            constraint=models.UniqueConstraint(
                fields=("card_pool", "card_identity_id"),
                name="ux_tts_sheet_slot_pool_identity",
            ),
        ),
        migrations.RemoveField(model_name="card", name="is_hero"),
    ]

from __future__ import annotations

from typing import Any

from django.db import migrations, models
import django.db.models.deletion

import card_reader_core.models.base


EMPTY_FACTION_IDENTITY_KEY = "[]"


def nest_classification_evidence(apps: Any, _schema_editor: Any) -> None:
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")
    for item in ImportJobItem.objects.iterator():
        previous = item.classification_inference_json
        if not isinstance(previous, dict) or not previous:
            item.classification_inference_json = {}
            item.save(update_fields=["classification_inference_json"])
            continue
        role_evidence = dict(previous) if isinstance(previous, dict) else {}
        shared = {
            key: role_evidence.pop(key)
            for key in ("live_classification", "queued_target_classification")
            if key in role_evidence
        }
        item.classification_inference_json = {
            "roles": role_evidence,
            "factions": {},
            **shared,
        }
        item.save(update_fields=["classification_inference_json"])


def guard_and_flatten_classification_evidence(apps: Any, _schema_editor: Any) -> None:
    CardFactionAssignment = apps.get_model("card_reader_core", "CardFactionAssignment")
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    Template = apps.get_model("card_reader_core", "Template")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")

    unsupported: list[str] = []
    if CardFactionAssignment.objects.exists():
        unsupported.append("card faction assignments")
    if Card.objects.exclude(faction_identity_key=EMPTY_FACTION_IDENTITY_KEY).exists():
        unsupported.append("card faction identity namespaces")
    if CardAlias.objects.exclude(faction_identity_key=EMPTY_FACTION_IDENTITY_KEY).exists():
        unsupported.append("alias faction identity namespaces")
    if Template.objects.exclude(inferred_card_factions_json=[]).exists():
        unsupported.append("template faction hints")
    if ImportJob.objects.exclude(card_faction_override_json=[]).exists():
        unsupported.append("import faction overrides")
    if ImportJob.objects.exclude(template_faction_snapshot_json=[]).exists():
        unsupported.append("import template faction snapshots")
    if ImportJobItem.objects.exclude(resolved_card_factions_json=[]).exists():
        unsupported.append("resolved import factions")
    if ImportJobItem.objects.exclude(target_card_factions_snapshot_json=[]).exists():
        unsupported.append("target faction snapshots")
    if unsupported:
        raise RuntimeError(
            "Migration 0060 cannot be reversed while faction data exists in: "
            + ", ".join(unsupported)
            + "."
        )

    for item in ImportJobItem.objects.iterator():
        evidence = item.classification_inference_json
        payload = dict(evidence) if isinstance(evidence, dict) else {}
        faction_evidence = payload.get("factions")
        if isinstance(faction_evidence, dict) and any(
            value not in (None, [], {}, "") for value in faction_evidence.values()
        ):
            raise RuntimeError(
                "Migration 0060 cannot be reversed while faction inference evidence exists."
            )
        for key in ("live_classification", "queued_target_classification"):
            classification = payload.get(key)
            if isinstance(classification, dict) and classification.get("card_factions") not in (
                None,
                [],
            ):
                raise RuntimeError(
                    "Migration 0060 cannot be reversed while classification snapshots "
                    "contain factions."
                )
        roles = payload.get("roles")
        flattened = dict(roles) if isinstance(roles, dict) else {}
        for key in ("live_classification", "queued_target_classification"):
            if key in payload:
                flattened[key] = payload[key]
        item.classification_inference_json = flattened
        item.save(update_fields=["classification_inference_json"])


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0059_card_identity_pool_locks")]

    operations = [
        migrations.AddField(
            model_name="card",
            name="faction_identity_key",
            field=models.TextField(default=EMPTY_FACTION_IDENTITY_KEY, editable=False),
        ),
        migrations.AddField(
            model_name="cardalias",
            name="faction_identity_key",
            field=models.TextField(default=EMPTY_FACTION_IDENTITY_KEY, editable=False),
        ),
        migrations.RemoveConstraint(model_name="card", name="uq_card_pool_key"),
        migrations.RemoveConstraint(model_name="cardalias", name="uq_card_alias_pool_key"),
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
        migrations.CreateModel(
            name="CardFactionAssignment",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(default=card_reader_core.models.base.now_utc),
                ),
                (
                    "updated_at",
                    models.DateTimeField(default=card_reader_core.models.base.now_utc),
                ),
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
                    models.CharField(
                        choices=[
                            ("order", "Order"),
                            ("blood", "Blood"),
                            ("darkness", "Darkness"),
                        ],
                        db_index=True,
                        max_length=64,
                    ),
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
        migrations.AlterField(
            model_name="cardroleassignment",
            name="role",
            field=models.CharField(
                choices=[
                    ("hero", "Hero"),
                    ("boss", "Boss"),
                    ("location", "Location"),
                    ("boon", "Boon"),
                    ("event", "Event"),
                    ("shop_item", "Shop Item"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="inferred_card_factions_json",
            field=models.JSONField(default=list),
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
            name="template_faction_snapshot_json",
            field=models.JSONField(default=list),
        ),
        migrations.RenameField(
            model_name="importjob",
            old_name="card_role_inference_policy_version",
            new_name="classification_inference_policy_version",
        ),
        migrations.AlterField(
            model_name="importjob",
            name="classification_inference_policy_version",
            field=models.IntegerField(default=3),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="resolved_card_factions_json",
            field=models.JSONField(default=list),
        ),
        migrations.RenameField(
            model_name="importjobitem",
            old_name="card_role_inference_json",
            new_name="classification_inference_json",
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="target_card_factions_snapshot_json",
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(
            nest_classification_evidence,
            guard_and_flatten_classification_evidence,
        ),
    ]

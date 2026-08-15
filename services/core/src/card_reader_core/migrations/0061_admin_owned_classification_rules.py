from __future__ import annotations

from typing import Any

from django.db import migrations, models
import django.db.models.deletion
import card_reader_core.models.base


NON_TERMINAL_IMPORT_STATUSES = ("queued", "running", "canceling")


def preflight_non_terminal_import_jobs(apps: Any, _schema_editor: Any) -> None:
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    job_ids = list(
        ImportJob.objects.filter(status__in=NON_TERMINAL_IMPORT_STATUSES)
        .order_by("created_at")
        .values_list("id", flat=True)[:10]
    )
    if job_ids:
        joined_ids = ", ".join(str(job_id) for job_id in job_ids)
        raise RuntimeError(
            "Card classification rules cannot be migrated while import jobs are non-terminal. "
            "Finish, cancel, or reset these jobs first: " + joined_ids
        )


def guard_reverse_classification_data(apps: Any, _schema_editor: Any) -> None:
    CardClassificationRule = apps.get_model("card_reader_core", "CardClassificationRule")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    if CardClassificationRule.objects.exists():
        raise RuntimeError(
            "Card classification migration 0061 cannot be reversed while classification rules "
            "exist. Remove the rules explicitly before rolling back."
        )
    if ImportJob.objects.exclude(classification_rule_snapshot_json={}).exists():
        raise RuntimeError(
            "Card classification migration 0061 cannot be reversed while import jobs retain "
            "classification rule snapshots. Preserve or remove those audit snapshots explicitly "
            "before rolling back."
        )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0060_faction_classification")]

    operations = [
        migrations.RunPython(preflight_non_terminal_import_jobs, migrations.RunPython.noop),
        migrations.CreateModel(
            name="CardClassificationRule",
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
                    "card_pool",
                    models.CharField(
                        choices=[("player", "Player"), ("evil", "Evil"), ("neutral", "Neutral")],
                        db_index=True,
                        max_length=16,
                    ),
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
            options={"db_table": "card_classification_rule"},
        ),
        migrations.AddField(
            model_name="importjob",
            name="classification_rule_snapshot_json",
            field=models.JSONField(default=dict),
        ),
        migrations.RemoveField(
            model_name="importjob", name="classification_inference_policy_version"
        ),
        migrations.RemoveField(model_name="importjob", name="template_faction_snapshot_json"),
        migrations.RemoveField(model_name="importjob", name="template_role_snapshot_json"),
        migrations.RemoveField(model_name="template", name="inferred_card_factions_json"),
        migrations.RemoveField(model_name="template", name="inferred_card_roles_json"),
        migrations.AddConstraint(
            model_name="cardclassificationrule",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("source_kind", "tag"), ("tag__isnull", False), ("type__isnull", True))
                    | models.Q(
                        ("source_kind", "type"), ("tag__isnull", True), ("type__isnull", False)
                    )
                ),
                name="ck_classification_rule_source_fk",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardclassificationrule",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_kind", "tag")),
                fields=("card_pool", "target_kind", "target_key", "tag"),
                name="uq_class_rule_tag_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardclassificationrule",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_kind", "type")),
                fields=("card_pool", "target_kind", "target_key", "type"),
                name="uq_class_rule_type_target",
            ),
        ),
        migrations.AddIndex(
            model_name="cardclassificationrule",
            index=models.Index(
                fields=["card_pool", "enabled", "tag"], name="ix_class_rule_pool_tag"
            ),
        ),
        migrations.AddIndex(
            model_name="cardclassificationrule",
            index=models.Index(
                fields=["card_pool", "enabled", "type"], name="ix_class_rule_pool_type"
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, guard_reverse_classification_data),
    ]

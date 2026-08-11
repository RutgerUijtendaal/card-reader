from __future__ import annotations

from uuid import uuid4
from typing import Any

from django.db import migrations, models
import card_reader_core.models.base


def populate_creation_keys_and_warnings(apps: Any, _schema_editor: Any) -> None:
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")
    for job in ImportJob.objects.all().iterator():
        job.creation_key = str(uuid4())
        job.save(update_fields=["creation_key"])
    for item in ImportJobItem.objects.all().iterator():
        if item.warning_code or item.warning_message:
            item.warnings_json = [
                {
                    "code": item.warning_code or "legacy_import_warning",
                    "message": item.warning_message or "Import completed with a warning.",
                }
            ]
            item.save(update_fields=["warnings_json"])


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0055_index_image_stored_paths")]

    operations = [
        migrations.AddField(
            model_name="template",
            name="inferred_card_roles_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjob",
            name="creation_key",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="importjob",
            name="creation_fingerprint",
            field=models.TextField(default=""),
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
            name="template_role_snapshot_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjob",
            name="card_role_inference_policy_version",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="resolved_card_roles_json",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="card_role_inference_json",
            field=models.JSONField(default=dict),
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
        migrations.RunPython(populate_creation_keys_and_warnings, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="importjob",
            name="creation_key",
            field=models.TextField(default=card_reader_core.models.base.uuid_str, unique=True),
        ),
    ]

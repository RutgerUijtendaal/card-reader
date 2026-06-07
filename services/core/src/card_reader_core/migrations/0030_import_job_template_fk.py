from __future__ import annotations

from typing import Any

from django.db import migrations, models


def _migrate_import_job_template_keys_to_ids(apps: Any, _schema_editor: Any) -> None:
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    Template = apps.get_model("card_reader_core", "Template")

    template_ids_by_key = {
        template.key: template.id
        for template in Template.objects.all()
    }
    for job in ImportJob.objects.all().only("id", "template_id"):
        template_id = template_ids_by_key.get(job.template_id)
        if template_id is None:
            raise ValueError(f"ImportJob '{job.id}' references unknown template key '{job.template_id}'")
        ImportJob.objects.filter(id=job.id).update(template_id=template_id)


def _migrate_import_job_template_ids_to_keys(apps: Any, _schema_editor: Any) -> None:
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    Template = apps.get_model("card_reader_core", "Template")

    template_keys_by_id = {
        template.id: template.key
        for template in Template.objects.all()
    }
    for job in ImportJob.objects.all().only("id", "template_id"):
        template_key = template_keys_by_id.get(job.template_id)
        if template_key is None:
            raise ValueError(f"ImportJob '{job.id}' references unknown template id '{job.template_id}'")
        ImportJob.objects.filter(id=job.id).update(template_id=template_key)


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0029_card_version_parse_flags")]

    operations = [
        migrations.RunPython(
            _migrate_import_job_template_keys_to_ids,
            reverse_code=_migrate_import_job_template_ids_to_keys,
        ),
        migrations.AlterField(
            model_name="importjob",
            name="template_id",
            field=models.ForeignKey(
                db_column="template_id",
                on_delete=models.PROTECT,
                related_name="import_jobs",
                to="card_reader_core.template",
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField("importjob", "template_id", "template"),
            ],
        ),
    ]

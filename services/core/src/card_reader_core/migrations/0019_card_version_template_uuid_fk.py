from __future__ import annotations

from typing import Any

from django.db import migrations, models


def _migrate_card_version_template_keys_to_ids(apps: Any, _schema_editor: Any) -> None:
    CardVersion = apps.get_model("card_reader_core", "CardVersion")
    Template = apps.get_model("card_reader_core", "Template")

    template_ids_by_key = {
        template.key: template.id
        for template in Template.objects.all()
    }
    for version in CardVersion.objects.all().only("id", "template_id"):
        template_id = template_ids_by_key.get(version.template_id)
        if template_id is None:
            raise ValueError(f"CardVersion '{version.id}' references unknown template key '{version.template_id}'")
        CardVersion.objects.filter(id=version.id).update(template_id=template_id)


def _migrate_card_version_template_ids_to_keys(apps: Any, _schema_editor: Any) -> None:
    CardVersion = apps.get_model("card_reader_core", "CardVersion")
    Template = apps.get_model("card_reader_core", "Template")

    template_keys_by_id = {
        template.id: template.key
        for template in Template.objects.all()
    }
    for version in CardVersion.objects.all().only("id", "template_id"):
        template_key = template_keys_by_id.get(version.template_id)
        if template_key is None:
            raise ValueError(f"CardVersion '{version.id}' references unknown template id '{version.template_id}'")
        CardVersion.objects.filter(id=version.id).update(template_id=template_key)


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0018_card_groups")]

    operations = [
        migrations.AlterField(
            model_name="cardversion",
            name="template",
            field=models.ForeignKey(
                db_column="template_id",
                db_constraint=False,
                on_delete=models.PROTECT,
                related_name="card_versions",
                to="card_reader_core.template",
            ),
        ),
        migrations.RunPython(
            _migrate_card_version_template_keys_to_ids,
            reverse_code=_migrate_card_version_template_ids_to_keys,
        ),
        migrations.AlterField(
            model_name="cardversion",
            name="template",
            field=models.ForeignKey(
                db_column="template_id",
                on_delete=models.PROTECT,
                related_name="card_versions",
                to="card_reader_core.template",
            ),
        ),
    ]

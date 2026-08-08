from __future__ import annotations

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def reset_test_phase_tts_card_sheets(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    tts_card_sheet = apps.get_model("card_reader_core", "TtsCardSheet")
    tts_card_sheet.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0048_alter_tts_card_sheet_layout_version")]

    operations = [
        # Earlier application versions cannot read layout 3, and the deleted
        # test-phase assignments cannot be reconstructed safely during rollback.
        migrations.RunPython(reset_test_phase_tts_card_sheets),
        migrations.RemoveConstraint(
            model_name="ttscardsheet",
            name="ck_tts_sheet_next_slot_capacity",
        ),
        migrations.RemoveConstraint(
            model_name="ttscardsheetslot",
            name="ck_tts_sheet_slot_capacity",
        ),
        migrations.AlterField(
            model_name="ttscardsheet",
            name="layout_version",
            field=models.PositiveSmallIntegerField(default=3),
        ),
        migrations.AddConstraint(
            model_name="ttscardsheet",
            constraint=models.CheckConstraint(
                condition=models.Q(("next_slot_index__lte", 63)),
                name="ck_tts_sheet_next_slot_capacity",
            ),
        ),
        migrations.AddConstraint(
            model_name="ttscardsheetslot",
            constraint=models.CheckConstraint(
                condition=models.Q(("slot_index__lt", 63)),
                name="ck_tts_sheet_slot_capacity",
            ),
        ),
    ]

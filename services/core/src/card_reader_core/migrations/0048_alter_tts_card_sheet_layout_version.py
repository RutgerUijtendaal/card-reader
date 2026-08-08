from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0047_tts_card_sheets")]

    operations = [
        migrations.AlterField(
            model_name="ttscardsheet",
            name="layout_version",
            field=models.PositiveSmallIntegerField(default=2),
        ),
    ]

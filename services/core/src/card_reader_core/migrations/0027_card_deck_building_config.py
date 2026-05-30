from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("card_reader_core", "0026_card_lifecycle_status_import_item_warnings"),
    ]

    operations = [
        migrations.AddField(
            model_name="card",
            name="deck_building_config_json",
            field=models.JSONField(default=dict),
        ),
    ]

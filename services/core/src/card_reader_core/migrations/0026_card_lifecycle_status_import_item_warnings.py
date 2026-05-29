from __future__ import annotations

from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [("card_reader_core", "0025_card_aliases_and_merge_redirects")]

    operations = [
        migrations.AddField(
            model_name="card",
            name="lifecycle_status",
            field=models.CharField(
                choices=[("active", "Active"), ("deprecated", "Deprecated")],
                db_index=True,
                default="active",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="warning_code",
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="warning_message",
            field=models.TextField(blank=True, default=None, null=True),
        ),
    ]

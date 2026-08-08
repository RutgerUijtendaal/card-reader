from __future__ import annotations

import card_reader_core.models.base
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0048_alter_tts_card_sheet_layout_version")]

    operations = [
        migrations.CreateModel(
            name="WorkerHeartbeat",
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
                ("worker_key", models.CharField(db_index=True, max_length=80)),
                ("display_name", models.CharField(max_length=120)),
                (
                    "activity",
                    models.CharField(
                        choices=[("idle", "idle"), ("busy", "busy"), ("stopped", "stopped")],
                        default="idle",
                        max_length=16,
                    ),
                ),
                ("current_work_id", models.TextField(blank=True, default=None, null=True)),
                ("started_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                (
                    "last_heartbeat_at",
                    models.DateTimeField(db_index=True, default=card_reader_core.models.base.now_utc),
                ),
                ("stopped_at", models.DateTimeField(blank=True, default=None, null=True)),
            ],
            options={
                "db_table": "worker_heartbeat",
                "ordering": ["worker_key", "-last_heartbeat_at"],
            },
        ),
        migrations.AddIndex(
            model_name="workerheartbeat",
            index=models.Index(
                fields=["worker_key", "-last_heartbeat_at"],
                name="ix_worker_heartbeat_recent",
            ),
        ),
    ]

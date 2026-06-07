from __future__ import annotations

import card_reader_core.models.base
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("card_reader_core", "0030_import_job_template_fk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserNotification",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("event_type", models.TextField(db_index=True)),
                ("subject_type", models.TextField(blank=True, db_index=True, default="")),
                ("subject_id", models.TextField(blank=True, db_index=True, default="")),
                ("target_url", models.TextField(blank=True, default="")),
                ("title", models.TextField(default="")),
                ("message", models.TextField(blank=True, default="")),
                ("metadata_json", models.JSONField(default=dict)),
                ("dedupe_key", models.TextField(blank=True, db_index=True, default="")),
                ("event_count", models.IntegerField(default=1)),
                ("read_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("archived_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("last_event_at", models.DateTimeField()),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        db_column="actor_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="triggered_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        db_column="recipient_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_notification",
                "indexes": [
                    models.Index(
                        fields=["recipient", "read_at", "-last_event_at"],
                        name="ix_notification_recipient_read",
                    ),
                    models.Index(
                        fields=["recipient", "dedupe_key", "read_at"],
                        name="ix_notification_recipient_dedupe",
                    ),
                    models.Index(
                        fields=["event_type", "subject_type", "subject_id"],
                        name="ix_notification_subject",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(archived_at__isnull=True, dedupe_key__gt="", read_at__isnull=True),
                        fields=("recipient", "dedupe_key"),
                        name="ux_notification_active_dedupe",
                    ),
                ],
            },
        ),
    ]

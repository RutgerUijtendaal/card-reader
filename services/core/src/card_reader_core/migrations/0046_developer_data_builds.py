from __future__ import annotations

import card_reader_core.models.base
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("card_reader_core", "0045_developer_data_download_grants"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DeveloperDataBuild",
            fields=[
                (
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("bundle_version", models.CharField(max_length=80, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "queued"),
                            ("running", "running"),
                            ("succeeded", "succeeded"),
                            ("failed", "failed"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("is_active_build", models.BooleanField(default=True)),
                ("started_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("finished_at", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "format_version",
                    models.PositiveIntegerField(blank=True, default=None, null=True),
                ),
                ("sha256", models.CharField(blank=True, default="", max_length=64)),
                (
                    "size_bytes",
                    models.PositiveBigIntegerField(blank=True, default=None, null=True),
                ),
                ("error_message", models.TextField(blank=True, default="")),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="requested_by_user_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="developer_data_builds",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "developer_data_build",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="developerdatabuild",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active_build", True)),
                fields=("is_active_build",),
                name="uq_dev_data_single_active_build",
            ),
        ),
    ]

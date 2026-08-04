from __future__ import annotations

import card_reader_core.models.base
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("card_reader_core", "0044_backfill_notification_previous_versions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DeveloperDataDownloadGrant",
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
                ("code_hash", models.CharField(max_length=64, unique=True)),
                ("token_hash", models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ("bundle_version", models.TextField(blank=True, default=None, null=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("exchanged_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("token_expires_at", models.DateTimeField(blank=True, db_index=True, default=None, null=True)),
                ("last_download_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        db_column="user_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="developer_data_download_grants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "developer_data_download_grant",
                "indexes": [models.Index(fields=["user", "expires_at"], name="ix_dev_data_grant_user_exp")],
            },
        ),
    ]

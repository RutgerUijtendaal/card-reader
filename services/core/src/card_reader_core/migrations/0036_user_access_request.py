from __future__ import annotations

import card_reader_core.models.base
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("card_reader_core", "0035_card_query_indexes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserAccessRequest",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("contact_handle", models.TextField()),
                ("normalized_contact_handle", models.TextField(db_index=True)),
                ("message", models.TextField(blank=True, default="")),
                ("status", models.TextField(db_index=True, default="pending")),
                ("resolved_at", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "created_user",
                    models.ForeignKey(
                        blank=True,
                        db_column="created_user_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="access_request_approvals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "resolved_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="resolved_by_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="resolved_access_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_access_request",
                "indexes": [
                    models.Index(fields=["status", "-created_at"], name="ix_access_request_status"),
                    models.Index(
                        fields=["normalized_contact_handle", "status"],
                        name="ix_access_request_contact_status",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(status__in=("pending", "approved", "declined")),
                        name="ck_access_request_status",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(status="pending"),
                        fields=("normalized_contact_handle",),
                        name="ux_access_request_pending_contact",
                    ),
                ],
            },
        ),
    ]

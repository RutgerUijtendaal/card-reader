from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class UserActivity(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    user: models.OneToOneField[AbstractUser, AbstractUser] = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="card_reader_activity",
        db_column="user_id",
    )
    last_active_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "user_activity"
        indexes = [
            models.Index(fields=["user", "-last_active_at"], name="ix_user_activity_user_time"),
        ]

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class DeveloperDataBuildStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class DeveloperDataBuild(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    requested_by: models.ForeignKey[AbstractUser | None, AbstractUser | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="developer_data_builds",
        db_column="requested_by_user_id",
        null=True,
        blank=True,
    )
    bundle_version: models.CharField[str, str] = models.CharField(max_length=80, unique=True)
    status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[(value.value, value.value) for value in DeveloperDataBuildStatus],
        default=DeveloperDataBuildStatus.queued,
        db_index=True,
    )
    is_active_build: models.BooleanField[bool, bool] = models.BooleanField(default=True)
    started_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )
    finished_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )
    format_version: models.PositiveIntegerField[int | None, int | None] = models.PositiveIntegerField(
        default=None,
        null=True,
        blank=True,
    )
    sha256: models.CharField[str, str] = models.CharField(max_length=64, blank=True, default="")
    size_bytes: models.PositiveBigIntegerField[int | None, int | None] = (
        models.PositiveBigIntegerField(default=None, null=True, blank=True)
    )
    error_message: models.TextField[str, str] = models.TextField(blank=True, default="")

    class Meta:
        db_table = "developer_data_build"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active_build"],
                condition=models.Q(is_active_build=True),
                name="uq_dev_data_single_active_build",
            ),
        ]


class DeveloperDataDownloadGrant(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    user: models.ForeignKey[AbstractUser, AbstractUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="developer_data_download_grants",
        db_column="user_id",
    )
    code_hash: models.CharField[str, str] = models.CharField(max_length=64, unique=True)
    token_hash: models.CharField[str | None, str | None] = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    bundle_version: models.TextField[str | None, str | None] = models.TextField(
        default=None,
        null=True,
        blank=True,
    )
    expires_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(db_index=True)
    exchanged_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )
    token_expires_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        db_index=True,
    )
    last_download_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )
    revoked_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "developer_data_download_grant"
        indexes = [
            models.Index(fields=["user", "expires_at"], name="ix_dev_data_grant_user_exp"),
        ]

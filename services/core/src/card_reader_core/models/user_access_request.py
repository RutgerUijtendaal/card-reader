from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


ACCESS_REQUEST_STATUS_PENDING = "pending"
ACCESS_REQUEST_STATUS_APPROVED = "approved"
ACCESS_REQUEST_STATUS_DECLINED = "declined"
ACCESS_REQUEST_STATUSES = (
    ACCESS_REQUEST_STATUS_PENDING,
    ACCESS_REQUEST_STATUS_APPROVED,
    ACCESS_REQUEST_STATUS_DECLINED,
)
ACCESS_REQUEST_STATUS_FILTER_ALL = "all"
ACCESS_REQUEST_STATUS_FILTERS = (
    ACCESS_REQUEST_STATUS_PENDING,
    ACCESS_REQUEST_STATUS_FILTER_ALL,
)


class UserAccessRequest(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    contact_handle: models.TextField[str, str] = models.TextField()
    normalized_contact_handle: models.TextField[str, str] = models.TextField(db_index=True)
    message: models.TextField[str, str] = models.TextField(default="", blank=True)
    status: models.TextField[str, str] = models.TextField(
        default=ACCESS_REQUEST_STATUS_PENDING,
        db_index=True,
    )
    resolved_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )
    resolved_by: models.ForeignKey[AbstractUser | None, AbstractUser | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="resolved_access_requests",
        db_column="resolved_by_id",
        default=None,
        null=True,
        blank=True,
    )
    created_user: models.ForeignKey[AbstractUser | None, AbstractUser | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="access_request_approvals",
        db_column="created_user_id",
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "user_access_request"
        indexes = [
            models.Index(fields=["status", "-created_at"], name="ix_access_request_status"),
            models.Index(
                fields=["normalized_contact_handle", "status"],
                name="ix_access_request_contact_status",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=ACCESS_REQUEST_STATUSES),
                name="ck_access_request_status",
            ),
            models.UniqueConstraint(
                fields=["normalized_contact_handle"],
                condition=models.Q(status=ACCESS_REQUEST_STATUS_PENDING),
                name="ux_access_request_pending_contact",
            ),
        ]

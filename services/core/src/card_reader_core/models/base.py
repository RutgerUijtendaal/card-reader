from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from django.db import models


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuid_str() -> str:
    return str(uuid4())


class TimestampedModel(models.Model):
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(default=now_utc)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(default=now_utc)

    class Meta:
        abstract = True



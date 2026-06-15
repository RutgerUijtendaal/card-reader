from __future__ import annotations

from datetime import datetime, timedelta

from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError
from django.db.models import Q

from card_reader_core.models import UserActivity, now_utc


def touch_user_activity(
    user: AbstractBaseUser,
    *,
    at: datetime | None = None,
    throttle_seconds: int = 300,
) -> bool:
    if not getattr(user, "is_authenticated", False) or user.pk is None:
        return False

    touched_at = at or now_utc()
    threshold = touched_at - timedelta(seconds=throttle_seconds)
    updated_count = UserActivity.objects.filter(user=user).filter(
        Q(last_active_at__lt=threshold),
    ).update(last_active_at=touched_at, updated_at=touched_at)
    if updated_count > 0:
        return True

    if UserActivity.objects.filter(user=user).exists():
        return False

    try:
        UserActivity.objects.create(
            user=user,
            last_active_at=touched_at,
            updated_at=touched_at,
        )
    except IntegrityError:
        return False
    return True

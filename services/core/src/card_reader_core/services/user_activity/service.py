from __future__ import annotations

from datetime import datetime
from typing import Iterable

from django.contrib.auth.models import AbstractBaseUser

from card_reader_core.repositories.user_activity import (
    get_last_active_by_user_id,
    touch_user_activity,
)


class UserActivityService:
    def get_last_active_by_user_id(self, user_ids: Iterable[object]) -> dict[object, datetime]:
        return get_last_active_by_user_id(user_ids)

    def touch_user(self, user: AbstractBaseUser, *, throttle_seconds: int = 300) -> bool:
        return touch_user_activity(user, throttle_seconds=throttle_seconds)

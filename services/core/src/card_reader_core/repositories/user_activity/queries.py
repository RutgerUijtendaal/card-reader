from __future__ import annotations

from datetime import datetime
from typing import Iterable

from card_reader_core.models import UserActivity


def get_last_active_by_user_id(user_ids: Iterable[object]) -> dict[object, datetime]:
    normalized_ids = [user_id for user_id in user_ids if user_id is not None]
    if not normalized_ids:
        return {}
    return {
        user_id: last_active_at
        for user_id, last_active_at in UserActivity.objects.filter(
            user_id__in=normalized_ids,
        ).values_list("user_id", "last_active_at")
    }

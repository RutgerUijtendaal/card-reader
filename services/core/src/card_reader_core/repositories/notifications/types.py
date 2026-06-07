from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from card_reader_core.models import UserNotification

NotificationStatusFilter = Literal["unread", "read", "all"]
NOTIFICATION_ALL_STATUS: NotificationStatusFilter = "all"


@dataclass(frozen=True)
class NotificationInput:
    recipient_id: str
    event_type: str
    subject_type: str
    subject_id: str
    target_url: str
    title: str
    message: str
    metadata: dict[str, object]
    actor_id: str | None = None
    dedupe_key: str = ""


@dataclass(frozen=True)
class PaginatedNotifications:
    count: int
    page: int
    page_size: int
    results: list[UserNotification]

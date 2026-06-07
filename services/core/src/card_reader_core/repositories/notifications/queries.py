from __future__ import annotations

from django.db.models import QuerySet

from card_reader_core.models import (
    NOTIFICATION_STATUS_FILTERS,
    NOTIFICATION_STATUS_READ,
    NOTIFICATION_STATUS_UNREAD,
    UserNotification,
)

from .types import NOTIFICATION_ALL_STATUS, NotificationStatusFilter, PaginatedNotifications


def is_notification_status_filter(value: object) -> bool:
    return isinstance(value, str) and value in NOTIFICATION_STATUS_FILTERS


def count_unread_notifications(recipient_id: str) -> int:
    return notification_queryset(recipient_id).filter(read_at__isnull=True).count()


def list_notifications(
    recipient_id: str,
    *,
    status: NotificationStatusFilter = NOTIFICATION_ALL_STATUS,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedNotifications:
    if not is_notification_status_filter(status):
        raise ValueError("Invalid notification status.")
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    queryset = notification_queryset(recipient_id)
    if status == NOTIFICATION_STATUS_UNREAD:
        queryset = queryset.filter(read_at__isnull=True)
    elif status == NOTIFICATION_STATUS_READ:
        queryset = queryset.filter(read_at__isnull=False)
    total_count = queryset.count()
    offset = (normalized_page - 1) * normalized_page_size
    return PaginatedNotifications(
        count=total_count,
        page=normalized_page,
        page_size=normalized_page_size,
        results=list(queryset[offset : offset + normalized_page_size]),
    )


def notification_queryset(recipient_id: str) -> QuerySet[UserNotification]:
    return (
        UserNotification.objects.select_related("recipient", "actor")
        .filter(recipient_id=recipient_id, archived_at__isnull=True)
        .order_by("-last_event_at", "-created_at", "id")
    )

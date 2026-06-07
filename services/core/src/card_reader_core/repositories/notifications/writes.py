from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import F, QuerySet

from card_reader_core.models import UserNotification, now_utc

from .queries import notification_queryset
from .types import NotificationInput, NotificationReadStateConflict


def create_or_coalesce_notification(data: NotificationInput) -> UserNotification:
    if data.dedupe_key:
        existing = _active_dedupe_queryset(data).order_by("-last_event_at", "-created_at").first()
        if existing is not None:
            return _coalesce_existing_notification(existing.id, data)
        try:
            with transaction.atomic():
                return _create_notification(data)
        except IntegrityError:
            existing = _active_dedupe_queryset(data).order_by("-last_event_at", "-created_at").first()
            if existing is None:
                raise
            return _coalesce_existing_notification(existing.id, data)

    return _create_notification(data)


def _active_dedupe_queryset(data: NotificationInput) -> QuerySet[UserNotification]:
    return UserNotification.objects.select_related("recipient", "actor").filter(
        recipient_id=data.recipient_id,
        dedupe_key=data.dedupe_key,
        read_at__isnull=True,
        archived_at__isnull=True,
    )


def _create_notification(data: NotificationInput) -> UserNotification:
    return UserNotification.objects.create(
        recipient_id=data.recipient_id,
        actor_id=data.actor_id,
        event_type=data.event_type,
        subject_type=data.subject_type,
        subject_id=data.subject_id,
        target_url=data.target_url,
        title=data.title,
        message=data.message,
        metadata_json=data.metadata,
        dedupe_key=data.dedupe_key,
        event_count=1,
        last_event_at=now_utc(),
    )


def _coalesce_existing_notification(notification_id: str, data: NotificationInput) -> UserNotification:
    now = now_utc()
    updated_count = (
        UserNotification.objects.filter(
            id=notification_id,
            read_at__isnull=True,
            archived_at__isnull=True,
        ).update(
            actor_id=data.actor_id,
            event_type=data.event_type,
            subject_type=data.subject_type,
            subject_id=data.subject_id,
            target_url=data.target_url,
            title=data.title,
            message=data.message,
            metadata_json=data.metadata,
            event_count=F("event_count") + 1,
            last_event_at=now,
            updated_at=now,
        )
    )
    if updated_count == 0:
        return _create_notification(data)
    return UserNotification.objects.select_related("recipient", "actor").get(id=notification_id)


def set_notification_read_state(
    *,
    notification_id: str,
    recipient_id: str,
    read: bool,
) -> UserNotification | None:
    notification = notification_queryset(recipient_id).filter(id=notification_id).first()
    if notification is None:
        return None
    if not read and notification.dedupe_key:
        conflicting_notification = (
            UserNotification.objects.select_related("recipient", "actor")
            .filter(
                recipient_id=recipient_id,
                dedupe_key=notification.dedupe_key,
                read_at__isnull=True,
                archived_at__isnull=True,
            )
            .exclude(id=notification.id)
            .order_by("-last_event_at", "-created_at")
            .first()
        )
        if conflicting_notification is not None:
            raise NotificationReadStateConflict(conflicting_notification)
    notification.read_at = now_utc() if read else None
    notification.updated_at = now_utc()
    notification.save(update_fields=["read_at", "updated_at"])
    return notification


def mark_all_notifications_read(recipient_id: str) -> int:
    now = now_utc()
    return (
        notification_queryset(recipient_id)
        .filter(read_at__isnull=True)
        .update(read_at=now, updated_at=now)
    )

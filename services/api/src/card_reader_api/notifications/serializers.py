from __future__ import annotations

from rest_framework import serializers

from card_reader_core.models import UserNotification


class NotificationQuerySerializer(serializers.Serializer[dict[str, object]]):
    status = serializers.ChoiceField(choices=["unread", "read", "all"], required=False, default="all")
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, default=50)


class NotificationUpdateSerializer(serializers.Serializer[dict[str, object]]):
    read = serializers.BooleanField()


def notification_payload(notification: UserNotification) -> dict[str, object]:
    actor = notification.actor
    return {
        "id": notification.id,
        "event_type": notification.event_type,
        "subject_type": notification.subject_type,
        "subject_id": notification.subject_id,
        "target_url": notification.target_url,
        "title": notification.title,
        "message": notification.message,
        "metadata": notification.metadata_json,
        "event_count": notification.event_count,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "created_at": notification.created_at.isoformat(),
        "updated_at": notification.updated_at.isoformat(),
        "last_event_at": notification.last_event_at.isoformat(),
        "actor": None
        if actor is None
        else {
            "id": str(actor.pk),
            "username": actor.get_username(),
        },
    }

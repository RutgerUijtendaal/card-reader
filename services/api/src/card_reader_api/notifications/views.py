from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.auth_access import is_authenticated
from card_reader_api.common.responses import serializer_error
from card_reader_api.notifications.serializers import (
    NotificationQuerySerializer,
    NotificationUpdateSerializer,
    notification_payload,
)
from card_reader_core.repositories.notifications import (
    count_unread_notifications,
    list_notifications,
    mark_all_notifications_read,
    set_notification_read_state,
)


class NotificationSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        user_id = _notification_user_id(request)
        if user_id is None:
            return Response({"unread_count": 0})
        return Response({"unread_count": count_unread_notifications(user_id)})


class NotificationListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        serializer = NotificationQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        user_id = _notification_user_id(request)
        if user_id is None:
            return Response(
                {
                    "count": 0,
                    "next_page": None,
                    "previous_page": None,
                    "page": serializer.validated_data["page"],
                    "page_size": serializer.validated_data["page_size"],
                    "results": [],
                }
            )
        page = list_notifications(
            user_id,
            status=serializer.validated_data["status"],
            page=serializer.validated_data["page"],
            page_size=serializer.validated_data["page_size"],
        )
        return Response(
            {
                "count": page.count,
                "next_page": page.page + 1 if page.page * page.page_size < page.count else None,
                "previous_page": page.page - 1 if page.page > 1 else None,
                "page": page.page,
                "page_size": page.page_size,
                "results": [notification_payload(notification) for notification in page.results],
            }
        )


class NotificationDetailView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request: Request, notification_id: str) -> Response:
        user_id = _notification_user_id(request)
        if user_id is None:
            return Response({"detail": "Authentication required."}, status=status.HTTP_403_FORBIDDEN)
        serializer = NotificationUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        notification = set_notification_read_state(
            notification_id=notification_id,
            recipient_id=user_id,
            read=bool(serializer.validated_data["read"]),
        )
        if notification is None:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(notification_payload(notification))


class MarkAllNotificationsReadView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        user_id = _notification_user_id(request)
        if user_id is None:
            return Response({"detail": "Authentication required."}, status=status.HTTP_403_FORBIDDEN)
        updated_count = mark_all_notifications_read(user_id)
        return Response({"updated_count": updated_count, "unread_count": 0})


def _notification_user_id(request: Request) -> str | None:
    if not settings.CARD_READER_AUTH_ENABLED or not is_authenticated(request.user):
        return None
    user_id = str(getattr(request.user, "pk", ""))
    return user_id or None

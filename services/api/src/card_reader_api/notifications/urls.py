from __future__ import annotations

from django.urls import path

from card_reader_api.notifications.views import (
    MarkAllNotificationsReadView,
    NotificationDetailView,
    NotificationListView,
    NotificationSummaryView,
)

urlpatterns = [
    path("notifications/summary", NotificationSummaryView.as_view()),
    path("notifications", NotificationListView.as_view()),
    path("notifications/mark-all-read", MarkAllNotificationsReadView.as_view()),
    path("notifications/<str:notification_id>", NotificationDetailView.as_view()),
]

from __future__ import annotations

from django.urls import path

from .views import (
    BackfillMetadataSuggestionsView,
    QueueLatestReparseView,
)

urlpatterns = [
    path("admin/maintenance/backfill-metadata-suggestions", BackfillMetadataSuggestionsView.as_view()),
    path("admin/maintenance/queue-latest-reparse", QueueLatestReparseView.as_view()),
]

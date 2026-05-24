from __future__ import annotations

from django.urls import path

from .views import (
    BackfillMetadataSuggestionsView,
    ClearStorageView,
    QueueLatestReparseView,
    RebuildDatabaseView,
)

urlpatterns = [
    path("admin/maintenance/rebuild-database", RebuildDatabaseView.as_view()),
    path("admin/maintenance/backfill-metadata-suggestions", BackfillMetadataSuggestionsView.as_view()),
    path("admin/maintenance/queue-latest-reparse", QueueLatestReparseView.as_view()),
    path("admin/maintenance/clear-storage", ClearStorageView.as_view()),
]

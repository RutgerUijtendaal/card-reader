from __future__ import annotations

from django.urls import path

from .views import ClearStorageView, OpenStorageLocationView, RebuildDatabaseView

urlpatterns = [
    path("settings/maintenance/rebuild-database", RebuildDatabaseView.as_view()),
    path("settings/maintenance/clear-storage", ClearStorageView.as_view()),
    path("settings/maintenance/open-storage-location", OpenStorageLocationView.as_view()),
]

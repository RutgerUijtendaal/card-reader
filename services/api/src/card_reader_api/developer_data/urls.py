from __future__ import annotations

from django.urls import path

from .views import (
    DeveloperDataBundleDownloadView,
    DeveloperDataBuildListView,
    DeveloperDataBuildLockView,
    DeveloperDataCurrentView,
    DeveloperDataGrantExchangeView,
    DeveloperDataGrantView,
)

urlpatterns = [
    path("developer-data/current", DeveloperDataCurrentView.as_view()),
    path("developer-data/grants", DeveloperDataGrantView.as_view()),
    path("developer-data/grants/exchange", DeveloperDataGrantExchangeView.as_view()),
    path("developer-data/builds", DeveloperDataBuildListView.as_view()),
    path(
        "developer-data/builds/<str:build_id>/lock",
        DeveloperDataBuildLockView.as_view(),
        name="developer-data-build-lock",
    ),
    path(
        "developer-data/bundles/<str:bundle_version>/download",
        DeveloperDataBundleDownloadView.as_view(),
    ),
]

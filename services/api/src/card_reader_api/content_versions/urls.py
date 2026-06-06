from __future__ import annotations

from django.urls import path

from .views import ContentVersionCardsView, ContentVersionDetailView, ContentVersionListView

urlpatterns = [
    path("admin/content-versions", ContentVersionListView.as_view()),
    path("admin/content-versions/<str:version_id>", ContentVersionDetailView.as_view()),
    path("admin/content-versions/<str:version_id>/cards", ContentVersionCardsView.as_view()),
]

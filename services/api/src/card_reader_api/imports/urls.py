from __future__ import annotations

from django.urls import path

from .views import ImportCancelView, ImportDetailView, ImportListView, ImportUploadView

urlpatterns = [
    path("imports", ImportListView.as_view()),
    path("imports/upload", ImportUploadView.as_view()),
    path("imports/<str:job_id>", ImportDetailView.as_view()),
    path("imports/<str:job_id>/cancel", ImportCancelView.as_view()),
]

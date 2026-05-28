from __future__ import annotations

from django.urls import path

from .views import CardMergeApplyView, CardMergePreviewView

urlpatterns = [
    path("admin/card-merges/preview", CardMergePreviewView.as_view()),
    path("admin/card-merges/apply", CardMergeApplyView.as_view()),
]

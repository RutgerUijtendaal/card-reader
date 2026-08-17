from __future__ import annotations

from django.urls import path

from .views import (
    TemplateDetailView,
    TemplateListCreateView,
    TemplatePreviewCardsView,
    TemplateReparseView,
)

urlpatterns = [
    path("admin/templates", TemplateListCreateView.as_view()),
    path("admin/templates/preview-cards", TemplatePreviewCardsView.as_view()),
    path("admin/templates/<str:entry_id>", TemplateDetailView.as_view()),
    path("admin/templates/<str:entry_id>/reparse", TemplateReparseView.as_view()),
]

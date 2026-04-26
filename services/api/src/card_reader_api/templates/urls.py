from __future__ import annotations

from django.urls import path

from .views import TemplateDetailView, TemplateListCreateView

urlpatterns = [
    path("settings/templates", TemplateListCreateView.as_view()),
    path("settings/templates/<str:entry_id>", TemplateDetailView.as_view()),
]

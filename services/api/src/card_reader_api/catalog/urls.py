from __future__ import annotations

from django.urls import path

from .views import (
    CatalogView,
    KeywordCreateView,
    KeywordDetailView,
    SymbolAssetUploadView,
    SymbolCreateView,
    SymbolDetailView,
    SuggestionAcceptView,
    SuggestionDetailView,
    SuggestionListView,
    SuggestionRejectView,
    TagCreateView,
    TagDetailView,
    TypeCreateView,
    TypeDetailView,
)

urlpatterns = [
    path("settings/catalog", CatalogView.as_view()),
    path("settings/keywords", KeywordCreateView.as_view()),
    path("settings/keywords/<str:entry_id>", KeywordDetailView.as_view()),
    path("settings/tags", TagCreateView.as_view()),
    path("settings/tags/<str:entry_id>", TagDetailView.as_view()),
    path("settings/types", TypeCreateView.as_view()),
    path("settings/types/<str:entry_id>", TypeDetailView.as_view()),
    path("settings/symbols", SymbolCreateView.as_view()),
    path("settings/symbols/<str:entry_id>", SymbolDetailView.as_view()),
    path("settings/symbols/assets/upload", SymbolAssetUploadView.as_view()),
    path("settings/suggestions/<str:kind>", SuggestionListView.as_view()),
    path("settings/suggestions/<str:kind>/<str:entry_id>", SuggestionDetailView.as_view()),
    path("settings/suggestions/<str:kind>/<str:entry_id>/accept", SuggestionAcceptView.as_view()),
    path("settings/suggestions/<str:kind>/<str:entry_id>/reject", SuggestionRejectView.as_view()),
]

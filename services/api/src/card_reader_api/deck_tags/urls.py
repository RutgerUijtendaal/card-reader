from django.urls import path

from .views import (
    AdminDeckTagCatalogView,
    AdminDeckTagDetailView,
    AdminDeckTagSuggestionAcceptView,
    AdminDeckTagSuggestionDetailView,
    AdminDeckTagSuggestionRejectView,
    DeckTagCatalogView,
)

urlpatterns = [
    path("deck-tags", DeckTagCatalogView.as_view()),
    path("admin/deck-tags", AdminDeckTagCatalogView.as_view()),
    path("admin/deck-tags/<str:tag_id>", AdminDeckTagDetailView.as_view()),
    path(
        "admin/deck-tag-suggestions/<str:suggestion_id>",
        AdminDeckTagSuggestionDetailView.as_view(),
    ),
    path(
        "admin/deck-tag-suggestions/<str:suggestion_id>/accept",
        AdminDeckTagSuggestionAcceptView.as_view(),
    ),
    path(
        "admin/deck-tag-suggestions/<str:suggestion_id>/reject",
        AdminDeckTagSuggestionRejectView.as_view(),
    ),
]

from django.urls import path

from .views import (
    DeckRulesMetadataView,
    OwnerDeckDetailView,
    OwnerDeckCreationLookupView,
    OwnerDeckListCreateView,
    PublicDeckDetailView,
    PublicDeckListView,
)

urlpatterns = [
    path("decks/rules", DeckRulesMetadataView.as_view()),
    path("decks", PublicDeckListView.as_view()),
    path("decks/<str:deck_id>", PublicDeckDetailView.as_view()),
    path("my/decks", OwnerDeckListCreateView.as_view()),
    path(
        "my/decks/by-creation-key/<uuid:client_creation_id>",
        OwnerDeckCreationLookupView.as_view(),
    ),
    path("my/decks/<str:deck_id>", OwnerDeckDetailView.as_view()),
]

from django.urls import path

from .views import OwnerDeckDetailView, OwnerDeckListCreateView, PublicDeckDetailView, PublicDeckListView

urlpatterns = [
    path("decks", PublicDeckListView.as_view()),
    path("decks/<str:deck_id>", PublicDeckDetailView.as_view()),
    path("my/decks", OwnerDeckListCreateView.as_view()),
    path("my/decks/<str:deck_id>", OwnerDeckDetailView.as_view()),
]

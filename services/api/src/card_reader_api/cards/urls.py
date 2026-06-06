from __future__ import annotations

from django.urls import path, re_path

from .views import (
    CardDetailView,
    CardFiltersView,
    CardGenerationsView,
    CardImageView,
    ImmutableCardImageView,
    CardListView,
    LatestCardReparseView,
    CardVersionImageView,
    CardVersionParseFlagView,
    CardVersionPromoteView,
    LatestCardVersionUpdateView,
    SymbolAssetView,
)

urlpatterns = [
    re_path(r"^card-images/(?P<relative_path>images/.*)$", ImmutableCardImageView.as_view()),
    path("cards", CardListView.as_view()),
    path("cards/filters", CardFiltersView.as_view()),
    path("cards/<str:card_id>", CardDetailView.as_view()),
    path("cards/<str:card_id>/generations", CardGenerationsView.as_view()),
    path("cards/<str:card_id>/latest-version", LatestCardVersionUpdateView.as_view()),
    path("cards/<str:card_id>/reparse", LatestCardReparseView.as_view()),
    path("cards/<str:card_id>/image", CardImageView.as_view()),
    path("cards/<str:card_id>/versions/<str:version_id>/promote", CardVersionPromoteView.as_view()),
    path("cards/<str:card_id>/versions/<str:version_id>/flags", CardVersionParseFlagView.as_view()),
    path("cards/<str:card_id>/versions/<str:version_id>/image", CardVersionImageView.as_view()),
    re_path(r"^symbols/assets/(?P<asset_path>.*)$", SymbolAssetView.as_view()),
]

from __future__ import annotations

from django.urls import path

from card_reader_api.review.views import ParseFlagItemDetailView, ParseFlagItemsView, ReviewSummaryView

urlpatterns = [
    path("review/summary", ReviewSummaryView.as_view()),
    path("review/parse-flags", ParseFlagItemsView.as_view()),
    path("review/parse-flags/items/<str:item_id>", ParseFlagItemDetailView.as_view()),
]

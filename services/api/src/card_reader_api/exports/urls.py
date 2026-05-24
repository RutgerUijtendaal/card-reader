from __future__ import annotations

from django.urls import path

from .views import DeckTtsExportView, ExportCsvView

urlpatterns = [
    path("exports/csv", ExportCsvView.as_view()),
    path("decks/<str:deck_id>/exports/tts", DeckTtsExportView.as_view()),
]

from __future__ import annotations

from django.urls import path

from .views import CardTtsExportView, DeckTtsExportView, ExportCsvView, TtsCardLibraryView

urlpatterns = [
    path("exports/csv", ExportCsvView.as_view()),
    path("exports/tts/cards", CardTtsExportView.as_view()),
    path("tts/card-library/cards.json", TtsCardLibraryView.as_view()),
    path("decks/<str:deck_id>/exports/tts", DeckTtsExportView.as_view()),
]

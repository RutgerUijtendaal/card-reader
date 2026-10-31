from django.urls import path

from .views import (
    EncounterCreationLookupView,
    EncounterRulesView,
    EncounterTtsView,
    EncounterBossPickerView,
    PublicEncounterDetailView,
    PublicEncounterListView,
    StaffEncounterDetailView,
    StaffEncounterListView,
)

urlpatterns = [
    path("encounters/rules", EncounterRulesView.as_view()),
    path("encounters", PublicEncounterListView.as_view()),
    path("encounters/<str:encounter_id>/exports/tts", EncounterTtsView.as_view()),
    path("encounters/<str:encounter_id>", PublicEncounterDetailView.as_view()),
    path("staff/encounters", StaffEncounterListView.as_view()),
    path("staff/encounters/bosses", EncounterBossPickerView.as_view()),
    path("staff/encounters/by-creation-key/<uuid:key>", EncounterCreationLookupView.as_view()),
    path("staff/encounters/<str:encounter_id>", StaffEncounterDetailView.as_view()),
]

from __future__ import annotations

from django.urls import path

from .views import (
    AdminCardBackDefaultView,
    AdminCardBackListView,
    AdminCardBackUploadView,
    CardBackDefaultsView,
    CurrentCardBackView,
)

urlpatterns = [
    path("card-backs/current", CurrentCardBackView.as_view()),
    path("card-backs/defaults", CardBackDefaultsView.as_view()),
    path("admin/card-backs", AdminCardBackListView.as_view()),
    path("admin/card-backs/upload", AdminCardBackUploadView.as_view()),
    path("admin/card-backs/defaults/<str:card_pool>", AdminCardBackDefaultView.as_view()),
]

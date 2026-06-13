from __future__ import annotations

from django.urls import path

from .views import AdminCardBackActivateView, AdminCardBackListView, AdminCardBackUploadView, CurrentCardBackView

urlpatterns = [
    path("card-backs/current", CurrentCardBackView.as_view()),
    path("admin/card-backs", AdminCardBackListView.as_view()),
    path("admin/card-backs/upload", AdminCardBackUploadView.as_view()),
    path("admin/card-backs/<str:card_back_id>/activate", AdminCardBackActivateView.as_view()),
]

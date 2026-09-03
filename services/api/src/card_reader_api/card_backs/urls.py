from __future__ import annotations

from django.urls import path

from .views import (
    AdminCardBackDefaultView,
    AdminCardBackFactionDefaultView,
    AdminCardBackListView,
    AdminCardBackRoleDefaultView,
    AdminCardBackUploadView,
    CardBackDefaultsView,
    CardBackFactionDefaultsView,
    CardBackRoleDefaultsView,
    CurrentCardBackView,
)

urlpatterns = [
    path("card-backs/current", CurrentCardBackView.as_view()),
    path("card-backs/defaults", CardBackDefaultsView.as_view()),
    path("card-backs/faction-defaults", CardBackFactionDefaultsView.as_view()),
    path("card-backs/role-defaults", CardBackRoleDefaultsView.as_view()),
    path("admin/card-backs", AdminCardBackListView.as_view()),
    path("admin/card-backs/upload", AdminCardBackUploadView.as_view()),
    path("admin/card-backs/defaults/<str:card_pool>", AdminCardBackDefaultView.as_view()),
    path(
        "admin/card-backs/faction-defaults/<str:faction>",
        AdminCardBackFactionDefaultView.as_view(),
    ),
    path(
        "admin/card-backs/role-defaults/<str:role>",
        AdminCardBackRoleDefaultView.as_view(),
    ),
]

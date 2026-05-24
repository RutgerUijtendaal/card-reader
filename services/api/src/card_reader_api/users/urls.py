from __future__ import annotations

from django.urls import path

from .views import (
    ManagedUserDetailView,
    ManagedUserListCreateView,
    ManagedUserResetPasswordView,
    ManagedUserRestoreView,
)

urlpatterns = [
    path("admin/users", ManagedUserListCreateView.as_view()),
    path("admin/users/<str:user_id>", ManagedUserDetailView.as_view()),
    path("admin/users/<str:user_id>/restore", ManagedUserRestoreView.as_view()),
    path("admin/users/<str:user_id>/reset-password", ManagedUserResetPasswordView.as_view()),
]

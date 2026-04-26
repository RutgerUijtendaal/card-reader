from __future__ import annotations

from django.urls import path

from .views import CurrentUserView, LoginView, LogoutView

urlpatterns = [
    path("login", LoginView.as_view()),
    path("logout", LogoutView.as_view()),
    path("me", CurrentUserView.as_view()),
]

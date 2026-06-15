from __future__ import annotations

from django.urls import path

from card_reader_api.access_requests.views import PublicAccessRequestView

from .views import CurrentUserView, LoginView, LogoutView, PasswordSetupView

urlpatterns = [
    path("login", LoginView.as_view()),
    path("logout", LogoutView.as_view()),
    path("me", CurrentUserView.as_view()),
    path("password/setup", PasswordSetupView.as_view()),
    path("access-requests", PublicAccessRequestView.as_view()),
]

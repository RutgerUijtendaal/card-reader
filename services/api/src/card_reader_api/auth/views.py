from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        username = str(request.data.get("username", ""))
        password = str(request.data.get("password", ""))
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        csrf_token = get_token(request)
        return Response(_user_payload(user, authenticated=True, csrf_token=csrf_token))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        csrf_token = get_token(request)
        if not request.user.is_authenticated:
            return Response(
                {
                    "auth_enabled": settings.CARD_READER_AUTH_ENABLED,
                    "authenticated": False,
                    "csrf_token": csrf_token,
                }
            )
        return Response(_user_payload(request.user, authenticated=True, csrf_token=csrf_token))


def _user_payload(user: Any, *, authenticated: bool, csrf_token: str) -> dict[str, object]:
    return {
        "auth_enabled": settings.CARD_READER_AUTH_ENABLED,
        "authenticated": authenticated,
        "csrf_token": csrf_token,
        "id": str(user.id),
        "username": user.get_username(),
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }

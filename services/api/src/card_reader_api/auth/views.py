from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import AbstractBaseUser
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.auth.password_flow import PasswordSetupService
from card_reader_api.common.auth_access import capability_payload


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
                    **capability_payload(None),
                }
            )
        return Response(_user_payload(request.user, authenticated=True, csrf_token=csrf_token))


class PasswordSetupView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        uid = str(request.query_params.get("uid", "")).strip()
        token = str(request.query_params.get("token", "")).strip()
        result = PasswordSetupService().validate(uid=uid, token=token)
        response_payload: dict[str, object] = {"valid": result.valid}
        if result.username:
            response_payload["username"] = result.username
        if result.detail:
            response_payload["detail"] = result.detail
        return Response(response_payload, status=status.HTTP_200_OK if result.valid else status.HTTP_400_BAD_REQUEST)

    def post(self, request: Request) -> Response:
        uid = str(request.data.get("uid", "")).strip()
        token = str(request.data.get("token", "")).strip()
        password = str(request.data.get("password", ""))
        try:
            user: AbstractBaseUser = PasswordSetupService().set_password(
                uid=uid,
                token=token,
                password=password,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Password set successfully.", "username": user.get_username()})


def _user_payload(user: Any, *, authenticated: bool, csrf_token: str) -> dict[str, object]:
    return {
        "auth_enabled": settings.CARD_READER_AUTH_ENABLED,
        "authenticated": authenticated,
        "csrf_token": csrf_token,
        "id": str(user.id),
        "username": user.get_username(),
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        **capability_payload(user),
    }

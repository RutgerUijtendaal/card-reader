from __future__ import annotations

from datetime import datetime
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from rest_framework import serializers

from card_reader_api.auth.password_flow import PasswordSetupLink


class ManagedUserListQuerySerializer(serializers.Serializer[dict[str, Any]]):
    include_inactive = serializers.BooleanField(required=False, default=False)


class ManagedUserCreateSerializer(serializers.Serializer[dict[str, Any]]):
    username = serializers.CharField(required=True, allow_blank=False, max_length=150, trim_whitespace=True)


def managed_user_payload(
    user: AbstractBaseUser,
    *,
    include_last_login: bool = True,
    include_last_active: bool = True,
    last_active_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "id": str(user.pk),
        "username": user.get_username(),
        "is_active": bool(getattr(user, "is_active", False)),
        "is_staff": bool(getattr(user, "is_staff", False)),
        "is_superuser": bool(getattr(user, "is_superuser", False)),
        "date_joined": _isoformat(getattr(user, "date_joined", None)),
        "last_login": _isoformat(getattr(user, "last_login", None)) if include_last_login else None,
        "last_active_at": _isoformat(last_active_at) if include_last_active else None,
    }


def password_setup_payload(user: AbstractBaseUser, link: PasswordSetupLink) -> dict[str, object]:
    return {
        "user": managed_user_payload(user),
        "uid": link.uid,
        "token": link.token,
        "setup_url": link.setup_url,
        "expires_in_seconds": link.expires_in_seconds,
    }


def _isoformat(value: object) -> str | None:
    if value is None or not hasattr(value, "isoformat"):
        return None
    return str(value.isoformat())

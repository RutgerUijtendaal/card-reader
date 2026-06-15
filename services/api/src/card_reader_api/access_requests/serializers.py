from __future__ import annotations

from typing import Any

from rest_framework import serializers

from card_reader_core.models import (
    ACCESS_REQUEST_STATUS_FILTERS,
    UserAccessRequest,
)


class AccessRequestCreateSerializer(serializers.Serializer[dict[str, Any]]):
    contact_handle = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=255,
        trim_whitespace=True,
    )
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True,
        default="",
    )


class AccessRequestListQuerySerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.ChoiceField(
        choices=ACCESS_REQUEST_STATUS_FILTERS,
        required=False,
        default="pending",
    )


class AccessRequestApproveSerializer(serializers.Serializer[dict[str, Any]]):
    username = serializers.CharField(required=True, allow_blank=False, max_length=150, trim_whitespace=True)


def access_request_payload(access_request: UserAccessRequest) -> dict[str, object]:
    return {
        "id": access_request.id,
        "contact_handle": access_request.contact_handle,
        "message": access_request.message,
        "status": access_request.status,
        "created_at": _isoformat(access_request.created_at),
        "updated_at": _isoformat(access_request.updated_at),
        "resolved_at": _isoformat(access_request.resolved_at),
        "resolved_by": _user_payload(access_request.resolved_by),
        "created_user": _user_payload(access_request.created_user),
    }


def _user_payload(user: Any | None) -> dict[str, object] | None:
    if user is None:
        return None
    username = user.get_username() if hasattr(user, "get_username") else str(user)
    return {
        "id": str(getattr(user, "pk", "")),
        "username": username,
    }


def _isoformat(value: object) -> str | None:
    if value is None or not hasattr(value, "isoformat"):
        return None
    return str(value.isoformat())

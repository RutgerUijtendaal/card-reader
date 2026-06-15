from __future__ import annotations

from django.db.models import QuerySet

from card_reader_core.models import (
    ACCESS_REQUEST_STATUS_FILTERS,
    ACCESS_REQUEST_STATUS_PENDING,
    UserAccessRequest,
)

from .types import ACCESS_REQUEST_ALL_STATUS, AccessRequestStatusFilter


def normalize_contact_handle(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def is_access_request_status_filter(value: object) -> bool:
    return isinstance(value, str) and value in ACCESS_REQUEST_STATUS_FILTERS


def list_access_requests(
    *,
    status: AccessRequestStatusFilter = "pending",
) -> list[UserAccessRequest]:
    if not is_access_request_status_filter(status):
        raise ValueError("Invalid access request status.")
    queryset = access_request_queryset()
    if status != ACCESS_REQUEST_ALL_STATUS:
        queryset = queryset.filter(status=status)
    return list(queryset)


def count_pending_access_requests() -> int:
    return access_request_queryset().filter(status=ACCESS_REQUEST_STATUS_PENDING).count()


def get_access_request(access_request_id: str) -> UserAccessRequest | None:
    return access_request_queryset().filter(id=access_request_id).first()


def get_pending_access_request_by_contact(normalized_contact_handle: str) -> UserAccessRequest | None:
    return (
        access_request_queryset()
        .filter(
            normalized_contact_handle=normalized_contact_handle,
            status=ACCESS_REQUEST_STATUS_PENDING,
        )
        .first()
    )


def access_request_queryset() -> QuerySet[UserAccessRequest]:
    return UserAccessRequest.objects.select_related("resolved_by", "created_user").order_by(
        "-created_at",
        "id",
    )

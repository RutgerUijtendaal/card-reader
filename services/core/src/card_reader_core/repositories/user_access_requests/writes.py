from __future__ import annotations

from django.db import IntegrityError, transaction

from card_reader_core.models import (
    ACCESS_REQUEST_STATUS_APPROVED,
    ACCESS_REQUEST_STATUS_DECLINED,
    ACCESS_REQUEST_STATUS_PENDING,
    UserAccessRequest,
    now_utc,
)

from .queries import get_access_request, get_pending_access_request_by_contact, normalize_contact_handle
from .types import AccessRequestSubmission


def create_or_get_pending_access_request(
    *,
    contact_handle: str,
    message: str = "",
) -> AccessRequestSubmission:
    normalized_contact_handle = normalize_contact_handle(contact_handle)
    if not normalized_contact_handle:
        raise ValueError("Contact handle is required.")

    existing = get_pending_access_request_by_contact(normalized_contact_handle)
    if existing is not None:
        return AccessRequestSubmission(
            access_request=_refresh_pending_access_request(
                existing,
                contact_handle=contact_handle.strip(),
                message=message.strip(),
            ),
            created=False,
        )

    try:
        with transaction.atomic():
            return AccessRequestSubmission(
                access_request=UserAccessRequest.objects.create(
                    contact_handle=contact_handle.strip(),
                    normalized_contact_handle=normalized_contact_handle,
                    message=message.strip(),
                ),
                created=True,
            )
    except IntegrityError:
        existing = get_pending_access_request_by_contact(normalized_contact_handle)
        if existing is None:
            raise
        return AccessRequestSubmission(
            access_request=_refresh_pending_access_request(
                existing,
                contact_handle=contact_handle.strip(),
                message=message.strip(),
            ),
            created=False,
        )


def approve_access_request(
    *,
    access_request_id: str,
    created_user_id: str,
    resolved_by_id: str,
) -> UserAccessRequest | None:
    now = now_utc()
    updated_count = UserAccessRequest.objects.filter(
        id=access_request_id,
        status=ACCESS_REQUEST_STATUS_PENDING,
    ).update(
        status=ACCESS_REQUEST_STATUS_APPROVED,
        created_user_id=created_user_id,
        resolved_by_id=resolved_by_id,
        resolved_at=now,
        updated_at=now,
    )
    if updated_count == 0:
        return None
    return get_access_request(access_request_id)


def decline_access_request(
    *,
    access_request_id: str,
    resolved_by_id: str,
) -> UserAccessRequest | None:
    now = now_utc()
    updated_count = UserAccessRequest.objects.filter(
        id=access_request_id,
        status=ACCESS_REQUEST_STATUS_PENDING,
    ).update(
        status=ACCESS_REQUEST_STATUS_DECLINED,
        resolved_by_id=resolved_by_id,
        resolved_at=now,
        updated_at=now,
    )
    if updated_count == 0:
        return None
    return get_access_request(access_request_id)


def _refresh_pending_access_request(
    access_request: UserAccessRequest,
    *,
    contact_handle: str,
    message: str,
) -> UserAccessRequest:
    update_fields: list[str] = []
    if contact_handle and access_request.contact_handle != contact_handle:
        access_request.contact_handle = contact_handle
        update_fields.append("contact_handle")
    if access_request.message != message:
        access_request.message = message
        update_fields.append("message")
    if update_fields:
        access_request.updated_at = now_utc()
        update_fields.append("updated_at")
        access_request.save(update_fields=update_fields)
    return access_request

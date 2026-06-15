from __future__ import annotations

from typing import TYPE_CHECKING

from card_reader_core.models import ACCESS_REQUEST_STATUS_PENDING, UserAccessRequest
from card_reader_core.repositories.user_access_requests import (
    AccessRequestStatusFilter,
    AccessRequestSubmission,
    count_pending_access_requests,
    create_or_get_pending_access_request,
    decline_access_request,
    get_access_request,
    list_access_requests,
)
from card_reader_core.repositories.user_access_requests import approve_access_request as approve_request

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


class AccessRequestNotFound(ValueError):
    pass


class AccessRequestAlreadyResolved(ValueError):
    pass


class UserAccessRequestService:
    def submit_request(self, *, contact_handle: str, message: str = "") -> AccessRequestSubmission:
        return create_or_get_pending_access_request(
            contact_handle=contact_handle,
            message=message,
        )

    def list_requests(
        self,
        *,
        status: AccessRequestStatusFilter = "pending",
    ) -> list[UserAccessRequest]:
        return list_access_requests(status=status)

    def count_pending_requests(self) -> int:
        return count_pending_access_requests()

    def get_pending_request(self, *, access_request_id: str) -> UserAccessRequest:
        access_request = get_access_request(access_request_id)
        if access_request is None:
            raise AccessRequestNotFound("Access request not found.")
        if access_request.status != ACCESS_REQUEST_STATUS_PENDING:
            raise AccessRequestAlreadyResolved("Access request has already been resolved.")
        return access_request

    def approve_request(
        self,
        *,
        access_request_id: str,
        created_user: AbstractBaseUser,
        resolved_by: AbstractBaseUser,
    ) -> UserAccessRequest:
        access_request = approve_request(
            access_request_id=access_request_id,
            created_user_id=str(created_user.pk),
            resolved_by_id=str(resolved_by.pk),
        )
        if access_request is None:
            self.get_pending_request(access_request_id=access_request_id)
            raise AccessRequestNotFound("Access request not found.")
        return access_request

    def decline_request(
        self,
        *,
        access_request_id: str,
        resolved_by: AbstractBaseUser,
    ) -> UserAccessRequest:
        access_request = decline_access_request(
            access_request_id=access_request_id,
            resolved_by_id=str(resolved_by.pk),
        )
        if access_request is None:
            self.get_pending_request(access_request_id=access_request_id)
            raise AccessRequestNotFound("Access request not found.")
        return access_request

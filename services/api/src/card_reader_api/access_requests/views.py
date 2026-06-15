from __future__ import annotations

from typing import cast

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.access_requests.serializers import (
    AccessRequestApproveSerializer,
    AccessRequestCreateSerializer,
    AccessRequestListQuerySerializer,
    access_request_payload,
)
from card_reader_api.auth.password_flow import PasswordSetupService
from card_reader_api.common.permissions import UserManagementAllowed
from card_reader_api.common.responses import bad_request, not_found, serializer_error
from card_reader_api.users.serializers import password_setup_payload
from card_reader_api.users.services import ManagedUserService
from card_reader_core.services.user_access_requests import (
    AccessRequestAlreadyResolved,
    AccessRequestNotFound,
    UserAccessRequestService,
)


class PublicAccessRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = AccessRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            result = UserAccessRequestService().submit_request(
                contact_handle=serializer.validated_data["contact_handle"],
                message=serializer.validated_data["message"],
            )
        except ValueError as exc:
            return bad_request(str(exc))
        response_status = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        return Response(access_request_payload(result.access_request), status=response_status)


class AdminAccessRequestListView(APIView):
    permission_classes = [UserManagementAllowed]

    def get(self, request: Request) -> Response:
        serializer = AccessRequestListQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        access_requests = UserAccessRequestService().list_requests(
            status=serializer.validated_data["status"],
        )
        return Response([access_request_payload(access_request) for access_request in access_requests])


class AdminAccessRequestSummaryView(APIView):
    permission_classes = [UserManagementAllowed]

    def get(self, _request: Request) -> Response:
        return Response(
            {
                "pending_access_request_count": UserAccessRequestService().count_pending_requests(),
            }
        )


class AdminAccessRequestApproveView(APIView):
    permission_classes = [UserManagementAllowed]

    def post(self, request: Request, access_request_id: str) -> Response:
        serializer = AccessRequestApproveSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        access_request_service = UserAccessRequestService()
        try:
            with transaction.atomic():
                access_request_service.get_pending_request(access_request_id=access_request_id)
                user = ManagedUserService().create_user(username=serializer.validated_data["username"])
                resolved_by = cast(AbstractBaseUser, request.user)
                access_request = access_request_service.approve_request(
                    access_request_id=access_request_id,
                    created_user=user,
                    resolved_by=resolved_by,
                )
        except AccessRequestNotFound:
            return not_found("Access request not found.")
        except AccessRequestAlreadyResolved as exc:
            return bad_request(str(exc))
        except ValueError as exc:
            return bad_request(str(exc))

        link = PasswordSetupService().build_setup_link(user, request._request)
        return Response(
            {
                "access_request": access_request_payload(access_request),
                "password_setup": password_setup_payload(user, link),
            }
        )


class AdminAccessRequestDeclineView(APIView):
    permission_classes = [UserManagementAllowed]

    def post(self, request: Request, access_request_id: str) -> Response:
        try:
            resolved_by = cast(AbstractBaseUser, request.user)
            access_request = UserAccessRequestService().decline_request(
                access_request_id=access_request_id,
                resolved_by=resolved_by,
            )
        except AccessRequestNotFound:
            return not_found("Access request not found.")
        except AccessRequestAlreadyResolved as exc:
            return bad_request(str(exc))
        return Response(access_request_payload(access_request))

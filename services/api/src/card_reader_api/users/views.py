from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.auth.password_flow import PasswordSetupService
from card_reader_api.common.permissions import AuthEnabledOrUserManagementAllowed
from card_reader_api.common.responses import bad_request, not_found, serializer_error
from card_reader_api.users.serializers import (
    ManagedUserCreateSerializer,
    ManagedUserListQuerySerializer,
    managed_user_payload,
    password_setup_payload,
)
from card_reader_api.users.services import ManagedUserService
from card_reader_core.services.user_activity import UserActivityService


class ManagedUserListCreateView(APIView):
    permission_classes = [AuthEnabledOrUserManagementAllowed]

    def get(self, request: Request) -> Response:
        serializer = ManagedUserListQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        managed_users, unmanaged_users = ManagedUserService().list_users(
            include_inactive=serializer.validated_data["include_inactive"],
        )
        include_activity = bool(getattr(request.user, "is_superuser", False))
        last_active_by_user_id = (
            UserActivityService().get_last_active_by_user_id(
                [user.pk for user in [*managed_users, *unmanaged_users]],
            )
            if include_activity
            else {}
        )
        return Response(
            {
                "managed_results": [
                    managed_user_payload(
                        user,
                        include_last_login=include_activity,
                        include_last_active=include_activity,
                        last_active_at=last_active_by_user_id.get(user.pk),
                    )
                    for user in managed_users
                ],
                "unmanaged_results": [
                    managed_user_payload(
                        user,
                        include_last_login=include_activity,
                        include_last_active=include_activity,
                        last_active_at=last_active_by_user_id.get(user.pk),
                    )
                    for user in unmanaged_users
                ],
            }
        )

    def post(self, request: Request) -> Response:
        serializer = ManagedUserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            user = ManagedUserService().create_user(username=serializer.validated_data["username"])
        except ValueError as exc:
            return bad_request(str(exc))
        link = PasswordSetupService().build_setup_link(user, request._request)
        return Response(password_setup_payload(user, link), status=status.HTTP_201_CREATED)


class ManagedUserDetailView(APIView):
    permission_classes = [AuthEnabledOrUserManagementAllowed]

    def delete(self, _request: Request, user_id: str) -> Response:
        user = ManagedUserService().deactivate_user(user_id=user_id)
        if user is None:
            return not_found("Managed user not found.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ManagedUserRestoreView(APIView):
    permission_classes = [AuthEnabledOrUserManagementAllowed]

    def post(self, _request: Request, user_id: str) -> Response:
        user = ManagedUserService().restore_user(user_id=user_id)
        if user is None:
            return not_found("Managed user not found.")
        return Response(managed_user_payload(user))


class ManagedUserResetPasswordView(APIView):
    permission_classes = [AuthEnabledOrUserManagementAllowed]

    def post(self, request: Request, user_id: str) -> Response:
        user = ManagedUserService().get_managed_user(user_id=user_id)
        if user is None:
            return not_found("Managed user not found.")
        link = PasswordSetupService().build_setup_link(user, request._request)
        return Response(password_setup_payload(user, link))

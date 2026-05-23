from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from card_reader_api.common.auth_access import (
    can_access_authenticated_features,
    can_access_maintenance,
    can_manage_settings,
    can_manage_users,
)


class AuthEnabledOrStaffAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        if not settings.CARD_READER_AUTH_ENABLED:
            return True
        return can_manage_settings(request.user)


class AuthEnabledOrSuperuserAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        if not settings.CARD_READER_AUTH_ENABLED:
            return True
        return can_access_maintenance(request.user)


class AuthEnabledOrAuthenticatedAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        if not settings.CARD_READER_AUTH_ENABLED:
            return True
        return can_access_authenticated_features(request.user)


class AuthEnabledOrUserManagementAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        if not settings.CARD_READER_AUTH_ENABLED:
            return True
        return can_manage_users(request.user)

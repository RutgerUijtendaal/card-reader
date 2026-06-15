from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from card_reader_api.common.auth_access import (
    can_access_authenticated_features,
    can_access_admin,
    can_access_maintenance,
    can_manage_users,
)


class StaffAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        return can_access_admin(request.user)


class SuperuserAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        return can_access_maintenance(request.user)


class AuthenticatedAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        return can_access_authenticated_features(request.user)


class UserManagementAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        return can_manage_users(request.user)

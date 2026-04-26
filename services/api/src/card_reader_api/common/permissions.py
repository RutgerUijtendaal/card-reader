from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class AuthEnabledOrReadWriteAllowed(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        if not settings.CARD_READER_AUTH_ENABLED:
            return True
        return bool(request.user and request.user.is_authenticated)

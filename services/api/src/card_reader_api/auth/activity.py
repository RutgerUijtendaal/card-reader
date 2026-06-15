from __future__ import annotations

import logging
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from card_reader_core.services.user_activity import UserActivityService

logger = logging.getLogger(__name__)


class UserActivityMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.activity_service = UserActivityService()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        self._touch_authenticated_user(request)
        return response

    def _touch_authenticated_user(self, request: HttpRequest) -> None:
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return
        try:
            self.activity_service.touch_user(user)
        except Exception:
            logger.exception("Failed to update user activity.")

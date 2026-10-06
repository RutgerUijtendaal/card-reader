from __future__ import annotations

import secrets

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_core.config.settings import settings
from card_reader_core.services.operations import MonitoringService


class MonitoringAllowed(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        expected = settings.monitoring_token
        supplied = request.headers.get("Authorization", "")
        return bool(expected) and secrets.compare_digest(
            supplied.encode("utf-8"), f"Bearer {expected}".encode("utf-8")
        )


class MonitoringView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [MonitoringAllowed]

    def get(self, _request: Request) -> Response:
        return Response(MonitoringService().build(), headers={"Cache-Control": "no-store"})

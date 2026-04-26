from __future__ import annotations

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_core.settings import settings


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        return Response({"status": "ok", "environment": settings.environment})

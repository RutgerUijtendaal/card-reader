from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse


class SimpleCorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = HttpResponse(status=204) if request.method == "OPTIONS" else self.get_response(request)
        origin = request.headers.get("origin")

        if settings.DEBUG and origin:
            response["Access-Control-Allow-Origin"] = origin
        elif origin and origin in getattr(settings, "CARD_READER_CORS_ORIGINS", []):
            response["Access-Control-Allow-Origin"] = origin

        response["Vary"] = "Origin"
        response["Access-Control-Allow-Methods"] = "GET,POST,PATCH,DELETE,OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-CSRFToken"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

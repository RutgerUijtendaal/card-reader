from __future__ import annotations

from urllib.parse import urljoin

from rest_framework.request import Request

from card_reader_core.config.settings import settings


def build_public_api_url(request: Request, path: str) -> str:
    configured_base_url = (settings.public_api_base_url or "").strip()
    base_url = configured_base_url or request.build_absolute_uri("/")
    return urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))

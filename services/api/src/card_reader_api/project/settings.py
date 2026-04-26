from __future__ import annotations

import json
import os

from card_reader_core import django_settings as core_django_settings
from card_reader_core.settings import settings as core_settings

for setting_name in dir(core_django_settings):
    if setting_name.isupper():
        globals()[setting_name] = getattr(core_django_settings, setting_name)

INSTALLED_APPS = [
    *core_django_settings.INSTALLED_APPS,
    "rest_framework",
    "card_reader_api.apps.CardReaderApiConfig",
]

MIDDLEWARE = [
    "card_reader_api.common.cors.SimpleCorsMiddleware",
    *core_django_settings.MIDDLEWARE,
]

ROOT_URLCONF = "card_reader_api.project.urls"
WSGI_APPLICATION = "card_reader_api.project.wsgi.application"
ASGI_APPLICATION = "card_reader_api.project.asgi.application"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "card_reader_api.common.permissions.AuthEnabledOrStaffAllowed",
    ],
}

_cors_raw = os.getenv("CARD_READER_CORS_ORIGINS", "")
try:
    CARD_READER_CORS_ORIGINS = json.loads(_cors_raw) if _cors_raw else core_settings.cors_origins
except json.JSONDecodeError:
    CARD_READER_CORS_ORIGINS = core_settings.cors_origins

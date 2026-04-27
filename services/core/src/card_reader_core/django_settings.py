from __future__ import annotations

import json
import os
from pathlib import Path

from card_reader_core.database.connection import DATABASE_PATH
from card_reader_core.settings import settings as core_settings


def _string_list_env(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default

    try:
        parsed_value = json.loads(raw_value)
    except json.JSONDecodeError:
        return [part.strip() for part in raw_value.split(",") if part.strip()]

    if isinstance(parsed_value, list):
        return [str(value).strip() for value in parsed_value if str(value).strip()]

    return default


def _csrf_origin_defaults() -> list[str]:
    return [
        origin
        for origin in core_settings.cors_origins
        if origin.startswith(("http://", "https://"))
    ]


BASE_DIR = Path(__file__).resolve().parents[4]
SECRET_KEY = os.getenv("CARD_READER_DJANGO_SECRET_KEY") or "card-reader-dev-secret-key"
DEBUG = core_settings.is_dev
ALLOWED_HOSTS = (
    ["*"]
    if DEBUG
    else _string_list_env("CARD_READER_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
)
CSRF_TRUSTED_ORIGINS = _string_list_env("CARD_READER_CSRF_TRUSTED_ORIGINS", _csrf_origin_defaults())
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "card_reader_core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DATABASE_PATH),
        "OPTIONS": {"timeout": 30},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CARD_READER_AUTH_ENABLED = os.getenv("CARD_READER_AUTH_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

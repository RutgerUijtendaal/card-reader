from __future__ import annotations

import os
from pathlib import Path

from card_reader_core.database.connection import DATABASE_PATH, initialize_database
from card_reader_core.settings import settings as core_settings

BASE_DIR = Path(__file__).resolve().parents[4]
SECRET_KEY = os.getenv("CARD_READER_DJANGO_SECRET_KEY", "card-reader-dev-secret-key")
DEBUG = core_settings.is_dev
ALLOWED_HOSTS = ["*"] if DEBUG else ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "card_reader_core.apps.CardReaderCoreConfig",
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

initialize_database()
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

CARD_READER_AUTH_ENABLED = os.getenv("CARD_READER_AUTH_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

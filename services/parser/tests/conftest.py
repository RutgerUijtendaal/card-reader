from __future__ import annotations

import os

os.environ["CARD_READER_ENV"] = "test"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_core.django_settings")

import django  # noqa: E402

django.setup()


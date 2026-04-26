from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ["CARD_READER_ENV"] = "test"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")

import django  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connections  # noqa: E402

django.setup()


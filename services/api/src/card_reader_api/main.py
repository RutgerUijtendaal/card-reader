from __future__ import annotations

import os

from card_reader_core.database.connection import initialize_database
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")
initialize_database()

app = get_asgi_application()

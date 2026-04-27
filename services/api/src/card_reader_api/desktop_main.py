from __future__ import annotations

import logging
import os
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import django

from card_reader_core.core_logging import configure_logging
from card_reader_core.database.connection import initialize_database

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")

from django.core.management import call_command  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402

logger = logging.getLogger(__name__)


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        logger.info("desktop-api %s", format % args)


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main() -> None:
    host = os.getenv("CARD_READER_API_HOST", "127.0.0.1")
    port = int(os.getenv("CARD_READER_API_PORT", "8000"))

    configure_logging()
    initialize_database()
    django.setup()
    call_command("migrate_card_reader")
    call_command("seed_users")
    call_command("seed_defaults")

    application = get_wsgi_application()
    with make_server(
        host,
        port,
        application,
        server_class=ThreadedWSGIServer,
        handler_class=QuietRequestHandler,
    ) as server:
        logger.info("Desktop API listening on %s:%s", host, port)
        server.serve_forever()


if __name__ == "__main__":
    main()

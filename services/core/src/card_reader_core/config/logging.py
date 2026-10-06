from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from logging.config import dictConfig
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        if record.stack_info:
            message += "\n" + self.formatStack(record.stack_info)
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "level": record.levelname.lower(),
                "logger": record.name,
                "message": message,
            },
            ensure_ascii=False,
        )


def logging_config() -> dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": JsonFormatter}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {
            "django": {"handlers": [], "propagate": True, "level": "INFO"},
            "django.server": {"handlers": [], "propagate": True, "level": "INFO"},
        },
    }


def configure_logging() -> None:
    dictConfig(logging_config())

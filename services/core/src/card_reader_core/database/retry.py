from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import logging
import time
from typing import ParamSpec, TypeVar

from django.db import OperationalError, connection

_SQLITE_WRITE_RETRY_ATTEMPTS = 6
_SQLITE_WRITE_RETRY_BASE_DELAY_SECONDS = 0.05
logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def run_with_sqlite_write_retry(operation: Callable[[], R]) -> R:
    """Retry a complete write operation after transient SQLite lock contention."""
    for attempt in range(_SQLITE_WRITE_RETRY_ATTEMPTS):
        try:
            return operation()
        except Exception as exc:
            if not _is_sqlite_lock_error(exc) or attempt == _SQLITE_WRITE_RETRY_ATTEMPTS - 1:
                raise
            delay_seconds = _SQLITE_WRITE_RETRY_BASE_DELAY_SECONDS * (2**attempt)
            logger.warning(
                "Transient SQLite lock contention; retrying atomic write. attempt=%s/%s delay_seconds=%.2f",
                attempt + 1,
                _SQLITE_WRITE_RETRY_ATTEMPTS,
                delay_seconds,
            )
            time.sleep(delay_seconds)
    raise RuntimeError("SQLite write retries were exhausted without raising an error.")


def retry_sqlite_write(operation: Callable[P, R]) -> Callable[P, R]:
    """Decorate an atomic write so each retry starts a fresh transaction."""

    @wraps(operation)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        return run_with_sqlite_write_retry(lambda: operation(*args, **kwargs))

    return wrapped


def _is_sqlite_lock_error(exc: BaseException) -> bool:
    if connection.vendor != "sqlite":
        return False

    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, OperationalError) and "locked" in str(current).lower():
            return True
        current = current.__cause__ or current.__context__
    return False

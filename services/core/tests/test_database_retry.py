from __future__ import annotations

import pytest
from django.db import OperationalError

from card_reader_core.database import retry as retry_module
from card_reader_core.database import run_with_sqlite_write_retry


def test_sqlite_write_retry_recognizes_wrapped_lock_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    delays: list[float] = []

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            try:
                raise OperationalError("database is locked")
            except OperationalError as exc:
                raise ValueError("domain error wrapping lock contention") from exc
        return "saved"

    monkeypatch.setattr(retry_module.time, "sleep", delays.append)

    assert run_with_sqlite_write_retry(operation) == "saved"
    assert attempts == 3
    assert delays == [0.05, 0.1]


def test_sqlite_write_retry_does_not_retry_unrelated_operational_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    delays: list[float] = []

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise OperationalError("database connection was lost")

    monkeypatch.setattr(retry_module.time, "sleep", delays.append)

    with pytest.raises(OperationalError, match="connection was lost"):
        run_with_sqlite_write_retry(operation)

    assert attempts == 1
    assert delays == []

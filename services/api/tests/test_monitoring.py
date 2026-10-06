from __future__ import annotations

from datetime import timedelta
import json
import logging
from pathlib import Path
import sqlite3
import time
from unittest.mock import patch

import pytest
from django.db import connection, OperationalError
from django.test import Client
from django.test.utils import CaptureQueriesContext
from pydantic import ValidationError

from card_reader_core.config.logging import JsonFormatter, configure_logging
from card_reader_core.config.settings import Settings, settings
from card_reader_core.models import ImportJob, Template, WorkerHeartbeat, now_utc
from card_reader_core.repositories.operations import monitoring_reads
from card_reader_core.services.operations import MonitoringService

TOKEN = "monitoring-test-" + "x" * 32


@pytest.mark.parametrize("token", ["x", "a" * 31, "a" * 129, "a" * 31 + "!", "a" * 32 + "\n"])
def test_invalid_monitoring_configuration_is_rejected(token: str) -> None:
    with pytest.raises(ValidationError):
        Settings(monitoring_token=token)


@pytest.mark.parametrize("token", ["", "a" * 32, "A0_-" * 32])
def test_monitoring_configuration_allows_disabled_and_valid_tokens(token: str) -> None:
    assert Settings(monitoring_token=token).monitoring_token == token


@pytest.fixture
def monitoring_client(monkeypatch: pytest.MonkeyPatch) -> Client:
    monkeypatch.setattr(settings, "monitoring_token", TOKEN)
    return Client(HTTP_HOST="localhost", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")


def test_authentication_is_independent_and_does_not_write(monitoring_client: Client) -> None:
    with CaptureQueriesContext(connection) as queries:
        response = monitoring_client.get("/internal/monitoring")
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert not any(
        item["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for item in queries
    )
    assert response.json()["database"] == "available"
    assert all(worker["health"] == "never_seen" for worker in response.json()["workers"])
    assert len(response.content) < 3500


@pytest.mark.parametrize("authorization", ["", "Basic wrong", "Bearer wrong"])
def test_invalid_auth_never_queries_database(monitoring_client: Client, authorization: str) -> None:
    with CaptureQueriesContext(connection) as queries:
        response = monitoring_client.get("/internal/monitoring", HTTP_AUTHORIZATION=authorization)
    assert response.status_code == 403
    assert len(queries) == 0


def test_unconfigured_endpoint_denies_even_empty_bearer(
    monitoring_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "monitoring_token", "")
    assert (
        monitoring_client.get("/internal/monitoring", HTTP_AUTHORIZATION="Bearer ").status_code
        == 403
    )


def test_database_failure_preserves_unknown_and_restores_connection(
    monitoring_client: Client,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA busy_timeout")
        original_timeout = cursor.fetchone()[0]
    with patch(
        "card_reader_core.services.operations.monitoring.OperationsOverviewService.build",
        side_effect=OperationalError("private database path"),
    ):
        response = monitoring_client.get("/internal/monitoring")
    payload = response.json()
    assert response.status_code == 200
    assert payload["database"] == "unavailable"
    assert payload["workers"] is None
    assert b"private" not in response.content
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA busy_timeout")
        assert cursor.fetchone()[0] == original_timeout
        cursor.execute("PRAGMA query_only")
        assert cursor.fetchone()[0] == 0


def test_monitoring_reads_reject_writes_and_bound_real_database_locks(tmp_path: Path) -> None:
    database = tmp_path / "locked.sqlite"
    reader = sqlite3.connect(database)
    writer = sqlite3.connect(database)
    try:
        reader.execute("CREATE TABLE fixture (value TEXT)")
        writer.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        with patch.object(connection, "connection", reader):
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                with monitoring_reads():
                    reader.execute("SELECT * FROM fixture")
        assert time.monotonic() - started < 2
        writer.rollback()
        with patch.object(connection, "connection", reader):
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                with monitoring_reads():
                    reader.execute("INSERT INTO fixture VALUES ('forbidden')")
        assert reader.execute("PRAGMA query_only").fetchone()[0] == 0
        assert reader.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    finally:
        reader.close()
        writer.close()


def test_monitoring_queue_counts_use_operational_classifications(monitoring_client: Client) -> None:
    baseline = monitoring_client.get("/internal/monitoring").json()
    before = next(worker["queue"] for worker in baseline["workers"] if worker["key"] == "parser")
    for status in ("queued", "queued", "failed", "completed"):
        ImportJob.objects.create(
            source_path="private-path",
            template=Template.objects.get(key="mtg-like-v1"),
            status=status,
        )
    payload = monitoring_client.get("/internal/monitoring").json()
    counts = next(worker["queue"] for worker in payload["workers"] if worker["key"] == "parser")
    assert counts["queued"] == before["queued"] + 2
    assert counts["failed"] == before["failed"] + 1
    assert counts["completed"] == before["completed"] + 1
    assert "private-path" not in json.dumps(payload)


@pytest.mark.parametrize(
    ("activity", "seconds_old", "stopped", "health"),
    [
        ("idle", 0, False, "online"),
        ("busy", 0, False, "online"),
        ("busy", 61, False, "stale"),
        ("stopped", 0, True, "stopped"),
    ],
)
def test_worker_states_and_timestamps(
    monitoring_client: Client, activity: str, seconds_old: int, stopped: bool, health: str
) -> None:
    now = now_utc()
    seen = now - timedelta(seconds=seconds_old)
    WorkerHeartbeat.objects.create(
        worker_key="parser",
        display_name="private name",
        activity=activity,
        last_heartbeat_at=seen,
        stopped_at=now if stopped else None,
        current_work_id="private-job",
    )
    payload = monitoring_client.get("/internal/monitoring").json()
    parser = next(worker for worker in payload["workers"] if worker["key"] == "parser")
    assert parser["health"] == health
    assert parser["last_seen_at"] == int(seen.timestamp())
    assert "private" not in json.dumps(payload)


def test_summary_supports_multiple_instances_and_wire_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for _ in range(2):
        WorkerHeartbeat.objects.create(
            worker_key="parser", display_name="Parser", last_heartbeat_at=now_utc()
        )
    payload = MonitoringService().build()
    parser = next(worker for worker in payload["workers"] if worker["key"] == "parser")
    assert parser["active_instances"] == 2
    fixture = json.loads((Path(__file__).parent / "fixtures/monitoring.json").read_text())
    assert payload.keys() == fixture.keys()
    assert parser.keys() == fixture["workers"][0].keys()
    assert parser["queue"].keys() == fixture["workers"][0]["queue"].keys()


def test_json_exception_is_one_record_and_reconfiguration_does_not_duplicate() -> None:
    previous = logging.getLogger().handlers[:]
    level = logging.getLogger().level
    try:
        configure_logging()
        configure_logging()
        assert len(logging.getLogger().handlers) == 1
        try:
            raise ValueError("synthetic failure")
        except ValueError:
            import sys

            record = logging.LogRecord(
                "fixture", logging.ERROR, __file__, 1, "Failed", (), sys.exc_info()
            )
        output = JsonFormatter().format(record)
        assert len(output.splitlines()) == 1
        value = json.loads(output)
        assert value["level"] == "error"
        assert "ValueError: synthetic failure" in value["message"]
    finally:
        logging.getLogger().handlers = previous
        logging.getLogger().setLevel(level)

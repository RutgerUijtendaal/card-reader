from __future__ import annotations

from datetime import datetime
import sqlite3
from typing import Any

from django.db import DatabaseError

from card_reader_core.config.settings import settings
from card_reader_core.models import now_utc
from card_reader_core.operations.workers import WORKER_HEARTBEAT_STALE_AFTER
from card_reader_core.repositories.operations.monitoring import monitoring_reads

from .overview import OperationsOverviewService


class MonitoringService:
    def build(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": 1,
            "observed_at": int(now_utc().timestamp()),
            "revision": settings.release_revision,
            "database": "unavailable",
            "stale_after_seconds": int(WORKER_HEARTBEAT_STALE_AFTER.total_seconds()),
            "workers": None,
        }
        try:
            with monitoring_reads():
                overview = OperationsOverviewService().build(include_items=False)
        except (DatabaseError, sqlite3.Error):
            return payload

        counts = {queue["worker_key"]: queue["status_counts"] for queue in overview["queues"]}
        payload["database"] = "available"
        payload["workers"] = [
            {
                "key": worker["key"],
                "health": worker["health"],
                "activity": worker["activity"],
                "active_instances": worker["active_instances"],
                "last_seen_at": (
                    int(datetime.fromisoformat(worker["last_seen_at"]).timestamp())
                    if worker["last_seen_at"] is not None
                    else None
                ),
                "queue": counts[worker["key"]],
            }
            for worker in overview["workers"]
        ]
        return payload

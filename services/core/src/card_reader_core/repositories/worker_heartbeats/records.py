from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db.models import Case, F, IntegerField, QuerySet, Value, When, Window
from django.db.models.functions import RowNumber

from card_reader_core.models import WorkerActivity, WorkerHeartbeat, now_utc

_OLD_INSTANCE_RETENTION = timedelta(days=7)


@dataclass(frozen=True)
class WorkerHeartbeatSnapshot:
    live_instances: tuple[WorkerHeartbeat, ...]
    fallback: WorkerHeartbeat | None


def register_worker(*, instance_id: str, worker_key: str, display_name: str) -> WorkerHeartbeat:
    now = now_utc()
    heartbeat, _created = WorkerHeartbeat.objects.update_or_create(
        id=instance_id,
        defaults={
            "worker_key": worker_key,
            "display_name": display_name,
            "activity": WorkerActivity.idle,
            "current_work_id": None,
            "started_at": now,
            "last_heartbeat_at": now,
            "stopped_at": None,
            "updated_at": now,
        },
    )
    _prune_old_instances(worker_key=worker_key, keep_instance_id=instance_id)
    return heartbeat


def heartbeat_worker(*, instance_id: str) -> None:
    now = now_utc()
    WorkerHeartbeat.objects.filter(id=instance_id, stopped_at__isnull=True).update(
        last_heartbeat_at=now,
        updated_at=now,
    )


def update_worker_activity(
    *,
    instance_id: str,
    activity: WorkerActivity,
    current_work_id: str | None,
) -> None:
    now = now_utc()
    WorkerHeartbeat.objects.filter(id=instance_id, stopped_at__isnull=True).update(
        activity=activity,
        current_work_id=current_work_id,
        last_heartbeat_at=now,
        updated_at=now,
    )


def stop_worker(*, instance_id: str) -> None:
    now = now_utc()
    WorkerHeartbeat.objects.filter(id=instance_id).update(
        activity=WorkerActivity.stopped,
        current_work_id=None,
        last_heartbeat_at=now,
        stopped_at=now,
        updated_at=now,
    )


def fetch_worker_heartbeat_snapshots(
    *,
    worker_keys: Iterable[str],
    stale_before: datetime,
) -> dict[str, WorkerHeartbeatSnapshot]:
    """Fetch live instances and at most one status fallback for each worker key."""
    keys = tuple(dict.fromkeys(worker_keys))
    if not keys:
        return {}

    live_by_key: dict[str, list[WorkerHeartbeat]] = {key: [] for key in keys}
    live_rows = WorkerHeartbeat.objects.filter(
        worker_key__in=keys,
        stopped_at__isnull=True,
        last_heartbeat_at__gte=stale_before,
    ).order_by("worker_key", "-last_heartbeat_at", "-id")
    for row in live_rows:
        live_by_key[row.worker_key].append(row)

    fallback_priority = Case(
        When(stopped_at__isnull=True, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    fallback_rows = (
        WorkerHeartbeat.objects.filter(worker_key__in=keys)
        .exclude(
            stopped_at__isnull=True,
            last_heartbeat_at__gte=stale_before,
        )
        .annotate(
            worker_rank=Window(
                expression=RowNumber(),
                partition_by=[F("worker_key")],
                order_by=[
                    fallback_priority.asc(),
                    F("last_heartbeat_at").desc(),
                    F("id").desc(),
                ],
            ),
        )
        .filter(worker_rank=1)
        .order_by("worker_key")
    )
    fallback_by_key = {row.worker_key: row for row in fallback_rows}

    return {
        key: WorkerHeartbeatSnapshot(
            live_instances=tuple(live_by_key[key]),
            fallback=fallback_by_key.get(key),
        )
        for key in keys
    }


def _prune_old_instances(*, worker_key: str, keep_instance_id: str) -> None:
    cutoff = now_utc() - _OLD_INSTANCE_RETENTION
    old_rows: QuerySet[WorkerHeartbeat] = WorkerHeartbeat.objects.filter(
        worker_key=worker_key,
        last_heartbeat_at__lt=cutoff,
    ).exclude(id=keep_instance_id)
    newest_old_id = old_rows.order_by("-last_heartbeat_at").values_list("id", flat=True).first()
    if newest_old_id is not None:
        old_rows = old_rows.exclude(id=newest_old_id)
    old_rows.delete()

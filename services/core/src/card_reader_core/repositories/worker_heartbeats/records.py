from __future__ import annotations

from datetime import timedelta

from django.db.models import QuerySet

from card_reader_core.models import WorkerActivity, WorkerHeartbeat, now_utc

_OLD_INSTANCE_RETENTION = timedelta(days=7)


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


def list_worker_heartbeats() -> list[WorkerHeartbeat]:
    return list(WorkerHeartbeat.objects.order_by("worker_key", "-last_heartbeat_at"))


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

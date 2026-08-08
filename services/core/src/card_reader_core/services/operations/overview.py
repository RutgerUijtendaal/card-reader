from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from card_reader_core.models import (
    DeveloperDataBuild,
    ImportJob,
    TtsCardSheet,
    WorkerActivity,
    WorkerHeartbeat,
    now_utc,
)
from card_reader_core.repositories.operations import (
    developer_data_build_status_counts,
    import_job_status_counts,
    list_import_jobs_for_operations,
    list_recent_developer_data_builds,
    list_tts_card_sheets_for_operations,
    tts_card_sheet_status_counts,
)
from card_reader_core.repositories.tts_card_sheets import (
    TTS_CARD_SHEET_RENDER_CLAIM_TIMEOUT,
)
from card_reader_core.repositories.worker_heartbeats import list_worker_heartbeats

_RECENT_ITEM_LIMIT = 20
_WORKER_STALE_AFTER = timedelta(seconds=30)

_EXPECTED_WORKERS = (
    ("parser", "Parser worker", "imports"),
    ("tts-sheet-renderer", "TTS card-sheet renderer", "tts-card-sheets"),
    ("developer-data-builder", "Developer-data builder", "developer-data-builds"),
)

_ALL_ITEM_STATUSES = (
    "scheduled",
    "queued",
    "running",
    "canceling",
    "retrying",
    "completed",
    "failed",
    "cancelled",
)


class OperationsOverviewService:
    def build(self) -> dict[str, Any]:
        now = now_utc()
        return {
            "generated_at": _iso(now),
            "stale_after_seconds": int(_WORKER_STALE_AFTER.total_seconds()),
            "workers": self._worker_payloads(now=now),
            "queues": [
                self._import_queue_payload(),
                self._tts_queue_payload(now=now),
                self._developer_data_queue_payload(),
            ],
        }

    def _worker_payloads(self, *, now: datetime) -> list[dict[str, Any]]:
        rows_by_key: dict[str, list[WorkerHeartbeat]] = {}
        for row in list_worker_heartbeats():
            rows_by_key.setdefault(row.worker_key, []).append(row)

        stale_before = now - _WORKER_STALE_AFTER
        payloads: list[dict[str, Any]] = []
        for worker_key, display_name, queue_key in _EXPECTED_WORKERS:
            rows = rows_by_key.get(worker_key, [])
            live = [
                row
                for row in rows
                if row.stopped_at is None and row.last_heartbeat_at >= stale_before
            ]
            latest = rows[0] if rows else None
            if live:
                activity = (
                    WorkerActivity.busy.value
                    if any(row.activity == WorkerActivity.busy for row in live)
                    else WorkerActivity.idle.value
                )
                health = "online"
                last_seen_at = max(row.last_heartbeat_at for row in live)
            elif latest is None:
                activity = WorkerActivity.stopped.value
                health = "never_seen"
                last_seen_at = None
            else:
                activity = str(latest.activity)
                health = "stopped" if latest.stopped_at is not None else "stale"
                last_seen_at = latest.last_heartbeat_at

            payloads.append(
                {
                    "key": worker_key,
                    "display_name": display_name,
                    "queue_key": queue_key,
                    "health": health,
                    "activity": activity,
                    "active_instances": len(live),
                    "last_seen_at": _iso(last_seen_at),
                    "current_work_ids": [
                        row.current_work_id
                        for row in live
                        if row.current_work_id is not None
                    ],
                }
            )
        return payloads

    def _import_queue_payload(self) -> dict[str, Any]:
        native_counts = import_job_status_counts()
        counts = _empty_counts()
        for status, count in native_counts.items():
            counts[_normalize_import_status(status)] += count
        items = [
            _import_item_payload(job)
            for job in list_import_jobs_for_operations(limit=_RECENT_ITEM_LIMIT)
        ]
        return _queue_payload(
            key="imports",
            display_name="Card imports",
            worker_key="parser",
            counts=counts,
            items=items,
        )

    def _tts_queue_payload(self, *, now: datetime) -> dict[str, Any]:
        counts = _empty_counts()
        counts.update(tts_card_sheet_status_counts(now=now))
        items = [
            _tts_item_payload(sheet, now=now)
            for sheet in list_tts_card_sheets_for_operations(limit=_RECENT_ITEM_LIMIT)
        ]
        return _queue_payload(
            key="tts-card-sheets",
            display_name="TTS card sheets",
            worker_key="tts-sheet-renderer",
            counts=counts,
            items=items,
        )

    def _developer_data_queue_payload(self) -> dict[str, Any]:
        native_counts = developer_data_build_status_counts()
        counts = _empty_counts()
        for status, count in native_counts.items():
            counts[_normalize_developer_data_status(status)] += count
        items = [
            _developer_data_item_payload(build)
            for build in list_recent_developer_data_builds(limit=_RECENT_ITEM_LIMIT)
        ]
        return _queue_payload(
            key="developer-data-builds",
            display_name="Developer-data builds",
            worker_key="developer-data-builder",
            counts=counts,
            items=items,
        )


def _queue_payload(
    *,
    key: str,
    display_name: str,
    worker_key: str,
    counts: dict[str, int],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "key": key,
        "display_name": display_name,
        "worker_key": worker_key,
        "total_count": sum(counts.values()),
        "status_counts": counts,
        "items": items,
    }


def _import_item_payload(job: ImportJob) -> dict[str, Any]:
    version = job.content_version.version_number if job.content_version is not None else "Unversioned"
    return {
        "id": job.id,
        "title": f"{job.template.label} · {version}",
        "status": _normalize_import_status(str(job.status)),
        "native_status": str(job.status),
        "created_at": _iso(job.created_at),
        "updated_at": _iso(job.updated_at),
        "started_at": None,
        "finished_at": None,
        "progress_current": job.processed_items,
        "progress_total": job.total_items,
        "error_message": None,
        "metadata": [
            {"label": "Template", "value": job.template.key},
            {"label": "Source", "value": job.source_path},
        ],
        "links": [],
    }


def _tts_item_payload(sheet: TtsCardSheet, *, now: datetime) -> dict[str, Any]:
    claim_is_active = _tts_claim_is_active(sheet, now=now)
    retry_at = (
        _iso(sheet.render_not_before)
        if sheet.render_failure_count > 0 and sheet.render_not_before is not None
        else None
    )
    metadata = [
        {"label": "Sheet", "value": str(sheet.sequence)},
        {"label": "Revision", "value": f"{sheet.rendered_revision}/{sheet.desired_revision}"},
    ]
    if retry_at is not None:
        metadata.append({"label": "Next attempt", "value": retry_at})
    return {
        "id": str(sheet.id),
        "title": f"Card sheet #{sheet.sequence}",
        "status": _tts_status(sheet, now=now),
        "native_status": None,
        "created_at": _iso(sheet.created_at),
        "updated_at": _iso(sheet.updated_at),
        "started_at": _iso(sheet.render_claimed_at) if claim_is_active else None,
        "finished_at": _iso(sheet.published_at),
        "progress_current": sheet.rendered_revision,
        "progress_total": sheet.desired_revision,
        "error_message": sheet.last_render_error or None,
        "metadata": metadata,
        "links": [],
    }


def _developer_data_item_payload(build: DeveloperDataBuild) -> dict[str, Any]:
    requested_by = build.requested_by.username if build.requested_by is not None else "Deleted user"
    metadata = [{"label": "Requested by", "value": requested_by}]
    if build.size_bytes is not None:
        metadata.append({"label": "Size", "value": str(build.size_bytes)})
    return {
        "id": build.id,
        "title": build.bundle_version,
        "status": _normalize_developer_data_status(str(build.status)),
        "native_status": str(build.status),
        "created_at": _iso(build.created_at),
        "updated_at": _iso(build.updated_at),
        "started_at": _iso(build.started_at),
        "finished_at": _iso(build.finished_at),
        "progress_current": None,
        "progress_total": None,
        "error_message": build.error_message or None,
        "metadata": metadata,
        "links": [],
    }


def _tts_status(sheet: TtsCardSheet, *, now: datetime) -> str:
    if sheet.desired_revision <= sheet.rendered_revision:
        return "completed"
    if _tts_claim_is_active(sheet, now=now):
        return "running"
    if sheet.render_failure_count > 0:
        return "retrying"
    if sheet.render_not_before is not None and sheet.render_not_before > now:
        return "scheduled"
    return "queued"


def _tts_claim_is_active(sheet: TtsCardSheet, *, now: datetime) -> bool:
    return (
        sheet.render_claimed_at is not None
        and sheet.render_claimed_at >= now - TTS_CARD_SHEET_RENDER_CLAIM_TIMEOUT
    )


def _normalize_import_status(status: str) -> str:
    return status if status in _ALL_ITEM_STATUSES else "failed"


def _normalize_developer_data_status(status: str) -> str:
    if status == "succeeded":
        return "completed"
    return status if status in _ALL_ITEM_STATUSES else "failed"


def _empty_counts() -> dict[str, int]:
    return {status: 0 for status in _ALL_ITEM_STATUSES}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None

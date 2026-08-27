from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from card_reader_core.models import (
    DeveloperDataBuild,
    ImportJob,
    TtsCardSheet,
    WorkerActivity,
    WorkerHeartbeat,
    now_utc,
)
from card_reader_core.operations.workers import WORKER_HEARTBEAT_STALE_AFTER
from card_reader_core.repositories.operations import (
    PaginatedOperationsRows,
    developer_data_build_status_counts,
    import_job_status_counts,
    list_import_jobs_for_operations,
    list_recent_developer_data_builds,
    list_tts_card_sheets_for_operations,
    paginate_developer_data_builds_for_operations,
    paginate_import_jobs_for_operations,
    paginate_tts_card_sheets_for_operations,
    tts_card_sheet_status_counts,
)
from card_reader_core.repositories.tts_card_sheets import (
    TTS_CARD_SHEET_RENDER_CLAIM_TIMEOUT,
)
from card_reader_core.repositories.worker_heartbeats import (
    fetch_worker_heartbeat_snapshots,
)

_RECENT_ITEM_LIMIT = 20

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

CountBuilder = Callable[[datetime], dict[str, int]]
RecentLoader = Callable[[int], list[Any]]
PageLoader = Callable[[int, int], PaginatedOperationsRows[Any]]
ItemBuilder = Callable[[Any, datetime], dict[str, Any]]


@dataclass(frozen=True)
class OperationsQueueDefinition:
    key: str
    display_name: str
    worker_key: str
    worker_display_name: str
    build_counts: CountBuilder
    load_recent: RecentLoader
    load_page: PageLoader
    build_item: ItemBuilder


class OperationsQueueNotFoundError(ValueError):
    pass


def _build_import_counts(_now: datetime) -> dict[str, int]:
    return _normalized_counts(import_job_status_counts(), _normalize_import_status)


def _load_recent_imports(limit: int) -> list[ImportJob]:
    return list_import_jobs_for_operations(limit=limit)


def _load_import_page(page: int, page_size: int) -> PaginatedOperationsRows[ImportJob]:
    return paginate_import_jobs_for_operations(page=page, page_size=page_size)


def _build_import_item(row: ImportJob, _now: datetime) -> dict[str, Any]:
    return _import_item_payload(row)


def _build_tts_counts(now: datetime) -> dict[str, int]:
    return _tts_counts(now=now)


def _load_recent_tts_sheets(limit: int) -> list[TtsCardSheet]:
    return list_tts_card_sheets_for_operations(limit=limit)


def _load_tts_sheet_page(
    page: int,
    page_size: int,
) -> PaginatedOperationsRows[TtsCardSheet]:
    return paginate_tts_card_sheets_for_operations(page=page, page_size=page_size)


def _build_tts_item(row: TtsCardSheet, now: datetime) -> dict[str, Any]:
    return _tts_item_payload(row, now=now)


def _build_developer_data_counts(_now: datetime) -> dict[str, int]:
    return _normalized_counts(
        developer_data_build_status_counts(),
        _normalize_developer_data_status,
    )


def _load_recent_developer_data_builds(limit: int) -> list[DeveloperDataBuild]:
    return list_recent_developer_data_builds(limit=limit)


def _load_developer_data_build_page(
    page: int,
    page_size: int,
) -> PaginatedOperationsRows[DeveloperDataBuild]:
    return paginate_developer_data_builds_for_operations(
        page=page,
        page_size=page_size,
    )


def _build_developer_data_item(
    row: DeveloperDataBuild,
    _now: datetime,
) -> dict[str, Any]:
    return _developer_data_item_payload(row)


_QUEUE_DEFINITIONS = (
    OperationsQueueDefinition(
        key="imports",
        display_name="Card imports",
        worker_key="parser",
        worker_display_name="Parser worker",
        build_counts=_build_import_counts,
        load_recent=_load_recent_imports,
        load_page=_load_import_page,
        build_item=_build_import_item,
    ),
    OperationsQueueDefinition(
        key="tts-card-sheets",
        display_name="TTS card sheets",
        worker_key="tts-sheet-renderer",
        worker_display_name="TTS card-sheet renderer",
        build_counts=_build_tts_counts,
        load_recent=_load_recent_tts_sheets,
        load_page=_load_tts_sheet_page,
        build_item=_build_tts_item,
    ),
    OperationsQueueDefinition(
        key="developer-data-builds",
        display_name="Developer-data builds",
        worker_key="developer-data-builder",
        worker_display_name="Developer-data builder",
        build_counts=_build_developer_data_counts,
        load_recent=_load_recent_developer_data_builds,
        load_page=_load_developer_data_build_page,
        build_item=_build_developer_data_item,
    ),
)

_QUEUE_DEFINITIONS_BY_KEY = {definition.key: definition for definition in _QUEUE_DEFINITIONS}


class OperationsOverviewService:
    def build(self, *, include_items: bool = True) -> dict[str, Any]:
        now = now_utc()
        return {
            "generated_at": _iso(now),
            "stale_after_seconds": int(WORKER_HEARTBEAT_STALE_AFTER.total_seconds()),
            "workers": self._worker_payloads(now=now),
            "queues": [
                self._queue_payload(
                    definition=definition,
                    now=now,
                    include_items=include_items,
                )
                for definition in _QUEUE_DEFINITIONS
            ],
        }

    def build_queue_page(
        self,
        *,
        queue_key: str,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        definition = _QUEUE_DEFINITIONS_BY_KEY.get(queue_key)
        if definition is None:
            raise OperationsQueueNotFoundError(queue_key)
        now = now_utc()
        rows = definition.load_page(page, page_size)
        return {
            "count": rows.count,
            "next_page": rows.page + 1 if rows.page * rows.page_size < rows.count else None,
            "previous_page": rows.page - 1 if rows.page > 1 else None,
            "page": rows.page,
            "page_size": rows.page_size,
            "results": [definition.build_item(row, now) for row in rows.results],
        }

    def _worker_payloads(self, *, now: datetime) -> list[dict[str, Any]]:
        stale_before = now - WORKER_HEARTBEAT_STALE_AFTER
        worker_definitions = {
            definition.worker_key: definition for definition in _QUEUE_DEFINITIONS
        }
        snapshots = fetch_worker_heartbeat_snapshots(
            worker_keys=worker_definitions,
            stale_before=stale_before,
        )
        payloads: list[dict[str, Any]] = []
        for worker_key, definition in worker_definitions.items():
            snapshot = snapshots[worker_key]
            live = snapshot.live_instances
            fallback = snapshot.fallback
            if live:
                activity = (
                    WorkerActivity.busy.value
                    if any(row.activity == WorkerActivity.busy for row in live)
                    else WorkerActivity.idle.value
                )
                health = "online"
                last_seen_at = max(row.last_heartbeat_at for row in live)
                visible_instances = live
            elif fallback is None:
                activity = WorkerActivity.stopped.value
                health = "never_seen"
                last_seen_at = None
                visible_instances = ()
            else:
                activity = str(fallback.activity)
                health = "stale" if fallback.stopped_at is None else "stopped"
                last_seen_at = fallback.last_heartbeat_at
                visible_instances = (fallback,)

            payloads.append(
                {
                    "key": worker_key,
                    "display_name": definition.worker_display_name,
                    "queue_key": definition.key,
                    "health": health,
                    "activity": activity,
                    "active_instances": len(live),
                    "last_seen_at": _iso(last_seen_at),
                    "current_work_ids": [
                        row.current_work_id
                        for row in live
                        if row.current_work_id is not None
                    ],
                    "instances": [
                        _worker_instance_payload(row=row, stale_before=stale_before)
                        for row in visible_instances
                    ],
                }
            )
        return payloads

    def _queue_payload(
        self,
        *,
        definition: OperationsQueueDefinition,
        now: datetime,
        include_items: bool,
    ) -> dict[str, Any]:
        counts = definition.build_counts(now)
        items = (
            [
                definition.build_item(row, now)
                for row in definition.load_recent(_RECENT_ITEM_LIMIT)
            ]
            if include_items
            else []
        )
        return {
            "key": definition.key,
            "display_name": definition.display_name,
            "worker_key": definition.worker_key,
            "total_count": sum(counts.values()),
            "status_counts": counts,
            "items": items,
        }


def _worker_instance_payload(
    *,
    row: WorkerHeartbeat,
    stale_before: datetime,
) -> dict[str, Any]:
    if row.stopped_at is not None:
        health = "stopped"
    elif row.last_heartbeat_at < stale_before:
        health = "stale"
    else:
        health = "online"
    return {
        "id": row.id,
        "display_name": row.display_name,
        "health": health,
        "activity": str(row.activity),
        "started_at": _iso(row.started_at),
        "last_seen_at": _iso(row.last_heartbeat_at),
        "stopped_at": _iso(row.stopped_at),
        "current_work_id": row.current_work_id,
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
            {"label": "Template", "value": job.template.label},
            {"label": "Card pool", "value": job.card_pool},
            {"label": "Role mode", "value": job.card_role_mode},
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


def _normalized_counts(
    native_counts: dict[str, int],
    normalize: Callable[[str], str],
) -> dict[str, int]:
    counts = _empty_counts()
    for status, count in native_counts.items():
        counts[normalize(status)] += count
    return counts


def _tts_counts(*, now: datetime) -> dict[str, int]:
    counts = _empty_counts()
    counts.update(tts_card_sheet_status_counts(now=now))
    return counts


def _empty_counts() -> dict[str, int]:
    return {status: 0 for status in _ALL_ITEM_STATUSES}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None

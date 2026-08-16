from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client

from card_reader_core.models import (
    DeveloperDataBuild,
    ImportJob,
    Template,
    TtsCardSheet,
    WorkerActivity,
    WorkerHeartbeat,
    now_utc,
)
from card_reader_core.operations.workers import WORKER_HEARTBEAT_STALE_AFTER
from card_reader_core.repositories.tts_card_sheets import (
    TTS_CARD_SHEET_RENDER_CLAIM_TIMEOUT,
)
from card_reader_core.repositories.worker_heartbeats import (
    fetch_worker_heartbeat_snapshots,
)
from card_reader_core.services.operations import OperationsOverviewService


def test_operations_overview_reports_workers_and_normalized_queues() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="operations-staff",
        password="password",
        is_staff=True,
    )
    now = now_utc()
    WorkerHeartbeat.objects.create(
        worker_key="parser",
        display_name="Parser worker",
        activity=WorkerActivity.busy,
        current_work_id="import-1",
        started_at=now,
        last_heartbeat_at=now,
    )
    ImportJob.objects.create(
        id="import-1",
        source_path="uploads/import-1",
        template=Template.objects.get(key="mtg-like-v1"),
        status="queued",
        total_items=2,
    )
    TtsCardSheet.objects.create(
        sequence=1001,
        desired_revision=1,
        render_not_before=now,
    )
    DeveloperDataBuild.objects.create(
        requested_by=staff,
        bundle_version="dev-operations-test",
        status="failed",
        is_active_build=False,
        error_message="Build failed for test.",
    )

    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)
    response = client.get("/operations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stale_after_seconds"] == int(WORKER_HEARTBEAT_STALE_AFTER.total_seconds())
    workers = {worker["key"]: worker for worker in payload["workers"]}
    assert workers["parser"]["health"] == "online"
    assert workers["parser"]["activity"] == "busy"
    assert workers["parser"]["current_work_ids"] == ["import-1"]
    assert workers["parser"]["instances"] == [
        {
            "id": workers["parser"]["instances"][0]["id"],
            "display_name": "Parser worker",
            "health": "online",
            "activity": "busy",
            "started_at": now.isoformat(),
            "last_seen_at": now.isoformat(),
            "stopped_at": None,
            "current_work_id": "import-1",
        }
    ]

    queues = {queue["key"]: queue for queue in payload["queues"]}
    assert queues["imports"]["status_counts"]["queued"] >= 1
    import_item = next(item for item in queues["imports"]["items"] if item["id"] == "import-1")
    assert {entry["label"]: entry["value"] for entry in import_item["metadata"]}["Template"] == (
        "MTG Like V1"
    )
    assert queues["tts-card-sheets"]["status_counts"]["queued"] >= 1
    assert queues["developer-data-builds"]["status_counts"]["failed"] >= 1


def test_operations_overview_prioritizes_stale_instance_over_stopped_history() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="stale-worker-staff",
        password="password",
        is_staff=True,
    )
    now = now_utc()
    stale_at = now - WORKER_HEARTBEAT_STALE_AFTER - timedelta(seconds=1)
    WorkerHeartbeat.objects.create(
        worker_key="parser",
        display_name="Parser worker",
        activity=WorkerActivity.busy,
        current_work_id="crashed-import",
        started_at=stale_at,
        last_heartbeat_at=stale_at,
    )
    WorkerHeartbeat.objects.create(
        worker_key="parser",
        display_name="Parser worker",
        activity=WorkerActivity.stopped,
        started_at=now,
        last_heartbeat_at=now,
        stopped_at=now,
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    response = client.get("/operations")

    assert response.status_code == 200
    workers = {worker["key"]: worker for worker in response.json()["workers"]}
    assert workers["parser"]["health"] == "stale"
    assert workers["parser"]["activity"] == "busy"
    assert workers["parser"]["last_seen_at"] == stale_at.isoformat()
    assert workers["parser"]["instances"][0]["health"] == "stale"


def test_worker_heartbeat_snapshot_bounds_inactive_history() -> None:
    now = now_utc()
    stale_at = now - WORKER_HEARTBEAT_STALE_AFTER - timedelta(seconds=1)
    stale = WorkerHeartbeat.objects.create(
        worker_key="parser",
        display_name="Parser worker",
        activity=WorkerActivity.busy,
        started_at=stale_at,
        last_heartbeat_at=stale_at,
    )
    WorkerHeartbeat.objects.bulk_create(
        [
            WorkerHeartbeat(
                worker_key="parser",
                display_name="Parser worker",
                activity=WorkerActivity.stopped,
                started_at=now - timedelta(seconds=index),
                last_heartbeat_at=now - timedelta(seconds=index),
                stopped_at=now - timedelta(seconds=index),
            )
            for index in range(50)
        ]
    )
    live = WorkerHeartbeat.objects.create(
        worker_key="parser",
        display_name="Parser worker",
        activity=WorkerActivity.idle,
        started_at=now,
        last_heartbeat_at=now,
    )

    snapshots = fetch_worker_heartbeat_snapshots(
        worker_keys=("parser",),
        stale_before=now - WORKER_HEARTBEAT_STALE_AFTER,
    )

    assert [row.id for row in snapshots["parser"].live_instances] == [live.id]
    assert snapshots["parser"].fallback == stale


def test_operations_overview_requires_staff() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="operations-regular-user",
        password="password",
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)

    assert client.get("/operations").status_code == 403
    assert client.get("/operations/queues/imports").status_code == 403


def test_operations_overview_can_skip_recent_items_and_reports_live_instances() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="operations-summary-staff",
        password="password",
        is_staff=True,
    )
    now = now_utc()
    for index in range(2):
        WorkerHeartbeat.objects.create(
            id=f"parser-instance-{index}",
            worker_key="parser",
            display_name="Parser worker",
            activity=WorkerActivity.idle,
            started_at=now,
            last_heartbeat_at=now,
        )
    ImportJob.objects.create(
        id="summary-import",
        source_path="uploads/summary-import",
        template=Template.objects.get(key="mtg-like-v1"),
        status="completed",
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    response = client.get("/operations", {"include_items": "false"})

    assert response.status_code == 200
    payload = response.json()
    queues = {queue["key"]: queue for queue in payload["queues"]}
    workers = {worker["key"]: worker for worker in payload["workers"]}
    assert queues["imports"]["total_count"] == 1
    assert queues["imports"]["items"] == []
    assert workers["parser"]["active_instances"] == 2
    assert {instance["id"] for instance in workers["parser"]["instances"]} == {
        "parser-instance-0",
        "parser-instance-1",
    }


def test_operations_queue_history_is_paginated_and_deterministically_ordered() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="operations-pagination-staff",
        password="password",
        is_staff=True,
    )
    template = Template.objects.get(key="mtg-like-v1")
    updated_at = now_utc() - timedelta(minutes=5)
    ImportJob.objects.bulk_create(
        [
            ImportJob(
                id=f"paged-import-{index:02d}",
                source_path=f"uploads/paged-import-{index:02d}",
                template=template,
                status="completed",
                created_at=updated_at,
                updated_at=updated_at,
            )
            for index in range(7)
        ]
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    response = client.get("/operations/queues/imports", {"page": 2, "page_size": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 7
    assert payload["page"] == 2
    assert payload["page_size"] == 3
    assert payload["previous_page"] == 1
    assert payload["next_page"] == 3
    assert [item["id"] for item in payload["results"]] == [
        "paged-import-03",
        "paged-import-04",
        "paged-import-05",
    ]

    response = client.get("/operations/queues/imports", {"page": 999, "page_size": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 3
    assert payload["previous_page"] == 2
    assert payload["next_page"] is None
    assert [item["id"] for item in payload["results"]] == ["paged-import-06"]


def test_operations_queue_history_validates_queue_and_pagination() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="operations-validation-staff",
        password="password",
        is_staff=True,
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    for queue_key in ("imports", "tts-card-sheets", "developer-data-builds"):
        response = client.get(f"/operations/queues/{queue_key}")
        assert response.status_code == 200
        assert response.json()["page_size"] == 20

    assert client.get("/operations/queues/not-a-queue").status_code == 404
    assert client.get("/operations/queues/imports", {"page": 0}).status_code == 400
    assert client.get("/operations/queues/imports", {"page_size": 101}).status_code == 400


def test_operations_overview_adds_developer_data_download_link_in_api_layer() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="operations-download-link-staff",
        password="password",
        is_staff=True,
    )
    build = DeveloperDataBuild.objects.create(
        requested_by=staff,
        bundle_version="dev-operations-download-link",
        status="succeeded",
        is_active_build=False,
    )
    core_payload = OperationsOverviewService().build()
    core_queues = {queue["key"]: queue for queue in core_payload["queues"]}
    core_items = {
        item["id"]: item for item in core_queues["developer-data-builds"]["items"]
    }
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    response = client.get("/operations")

    assert core_items[build.id]["links"] == []
    assert response.status_code == 200
    api_queues = {queue["key"]: queue for queue in response.json()["queues"]}
    api_items = {
        item["id"]: item for item in api_queues["developer-data-builds"]["items"]
    }
    assert api_items[build.id]["links"] == [
        {
            "label": "Download lock file",
            "href": f"/developer-data/builds/{build.id}/lock",
        }
    ]

    history_response = client.get("/operations/queues/developer-data-builds")
    assert history_response.status_code == 200
    history_items = {
        item["id"]: item for item in history_response.json()["results"]
    }
    assert history_items[build.id]["links"] == [
        {
            "label": "Download lock file",
            "href": f"/developer-data/builds/{build.id}/lock",
        }
    ]


def test_operations_overview_treats_expired_tts_claim_as_queued() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="stale-tts-claim-staff",
        password="password",
        is_staff=True,
    )
    now = now_utc()
    stale_sheet = TtsCardSheet.objects.create(
        sequence=1002,
        desired_revision=1,
        render_claimed_at=now - TTS_CARD_SHEET_RENDER_CLAIM_TIMEOUT - timedelta(seconds=1),
    )
    active_sheet = TtsCardSheet.objects.create(
        sequence=1003,
        desired_revision=1,
        render_claimed_at=now,
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    response = client.get("/operations")

    assert response.status_code == 200
    queues = {queue["key"]: queue for queue in response.json()["queues"]}
    tts_queue = queues["tts-card-sheets"]
    items = {item["id"]: item for item in tts_queue["items"]}
    assert items[str(stale_sheet.id)]["status"] == "queued"
    assert items[str(stale_sheet.id)]["started_at"] is None
    assert items[str(active_sheet.id)]["status"] == "running"


def test_operations_overview_keeps_recent_terminal_imports_when_active_queue_is_full() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="recent-terminal-import-staff",
        password="password",
        is_staff=True,
    )
    template = Template.objects.get(key="mtg-like-v1")
    older_at = now_utc() - timedelta(hours=1)
    ImportJob.objects.bulk_create(
        [
            ImportJob(
                id=f"older-active-import-{index}",
                source_path=f"uploads/older-active-{index}",
                template=template,
                status="queued",
                created_at=older_at,
                updated_at=older_at,
            )
            for index in range(20)
        ]
    )
    recent_failed = ImportJob.objects.create(
        id="recent-failed-import",
        source_path="uploads/recent-failed",
        template=template,
        status="failed",
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    response = client.get("/operations")

    assert response.status_code == 200
    queues = {queue["key"]: queue for queue in response.json()["queues"]}
    import_ids = {item["id"] for item in queues["imports"]["items"]}
    assert recent_failed.id in import_ids


def test_operations_overview_keeps_recent_completed_sheet_when_pending_queue_is_full() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="recent-completed-sheet-staff",
        password="password",
        is_staff=True,
    )
    older_at = now_utc() - timedelta(hours=1)
    TtsCardSheet.objects.bulk_create(
        [
            TtsCardSheet(
                sequence=2000 + index,
                desired_revision=1,
                created_at=older_at,
                updated_at=older_at,
            )
            for index in range(20)
        ]
    )
    recent_completed = TtsCardSheet.objects.create(
        sequence=2020,
        desired_revision=1,
        rendered_revision=1,
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    response = client.get("/operations")

    assert response.status_code == 200
    queues = {queue["key"]: queue for queue in response.json()["queues"]}
    sheet_ids = {item["id"] for item in queues["tts-card-sheets"]["items"]}
    assert recent_completed.id in sheet_ids


def test_import_list_active_filter_excludes_completed_jobs() -> None:
    user_model = get_user_model()
    staff = user_model.objects.create_user(
        username="active-import-staff",
        password="password",
        is_staff=True,
    )
    template = Template.objects.get(key="mtg-like-v1")
    ImportJob.objects.create(
        id="active-import",
        source_path="uploads/active",
        template=template,
        status="running",
    )
    ImportJob.objects.create(
        id="completed-import",
        source_path="uploads/completed",
        template=template,
        status="completed",
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)

    response = client.get("/imports", {"status": "active"})

    assert response.status_code == 200
    job_ids = {job["id"] for job in response.json()}
    assert "active-import" in job_ids
    assert "completed-import" not in job_ids

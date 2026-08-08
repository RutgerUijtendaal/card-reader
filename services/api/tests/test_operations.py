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
from card_reader_core.repositories.tts_card_sheets import (
    TTS_CARD_SHEET_RENDER_CLAIM_TIMEOUT,
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
    workers = {worker["key"]: worker for worker in payload["workers"]}
    assert workers["parser"]["health"] == "online"
    assert workers["parser"]["activity"] == "busy"
    assert workers["parser"]["current_work_ids"] == ["import-1"]

    queues = {queue["key"]: queue for queue in payload["queues"]}
    assert queues["imports"]["status_counts"]["queued"] >= 1
    assert queues["tts-card-sheets"]["status_counts"]["queued"] >= 1
    assert queues["developer-data-builds"]["status_counts"]["failed"] >= 1


def test_operations_overview_requires_staff() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="operations-regular-user",
        password="password",
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)

    assert client.get("/operations").status_code == 403


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

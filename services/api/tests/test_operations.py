from __future__ import annotations

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
    assert {job["id"] for job in response.json()} == {"active-import"}

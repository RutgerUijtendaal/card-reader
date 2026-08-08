from __future__ import annotations

from datetime import timedelta
import hashlib
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
import pytest

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    DeveloperDataBuild,
    DeveloperDataBuildStatus,
    DeveloperDataDownloadGrant,
)
from card_reader_core.operations.developer_data import DeveloperDataError, PublishedBundleStore
from card_reader_core.operations.developer_data.schema import PublishedBundle
from card_reader_core.repositories.developer_data import (
    mark_build_failed,
    mark_build_succeeded,
    requeue_interrupted_builds,
)
from card_reader_core.services.user_roles import set_developer_role


def test_developer_data_requires_an_active_authenticated_user() -> None:
    _publish_test_bundle("access-control")
    anonymous_response = Client(HTTP_HOST="localhost").get("/developer-data/current")
    anonymous_session = Client(HTTP_HOST="localhost").get("/auth/me")
    regular = _create_user("dev-data-regular")
    regular_client = Client(HTTP_HOST="localhost")
    regular_client.force_login(regular)
    inactive = _create_user("dev-data-inactive", is_active=False, is_developer=True)
    inactive_client = Client(HTTP_HOST="localhost")
    inactive_client.force_login(inactive)

    assert anonymous_response.status_code == 403
    assert anonymous_session.json()["can_download_developer_data"] is False
    assert regular_client.get("/developer-data/current").status_code == 403
    assert regular_client.get("/auth/me").json()["can_download_developer_data"] is False
    assert inactive_client.get("/developer-data/current").status_code == 403
    assert Client(HTTP_HOST="localhost").get(
        "/developer-data/bundles/..%2Fprivate/download"
    ).status_code in {400, 404}


def test_current_bundle_and_browser_download_are_available_to_regular_users() -> None:
    content = _publish_test_bundle("browser-download")
    user = _create_user("dev-data-browser", is_developer=True)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)

    current_response = client.get("/developer-data/current")
    download_response = client.get(
        "/developer-data/bundles/browser-download/download",
    )

    assert current_response.status_code == 200
    assert current_response.json()["available"] is True
    assert current_response.json()["bundle_version"] == "browser-download"
    assert download_response.status_code == 200
    download_body = b"".join(download_response.streaming_content)
    download_response.close()
    assert download_body == content
    assert download_response["Content-Disposition"].endswith(
        'filename="card-reader-dev-data-browser-download.tar.gz"'
    )
    assert download_response["Cache-Control"] == "private, no-store"
    assert download_response["X-Content-Type-Options"] == "nosniff"


def test_grant_creation_requires_csrf_and_replacement_revokes_the_old_code() -> None:
    _publish_test_bundle("grant-replacement")
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login(client, "dev-data-grant")

    assert client.post("/developer-data/grants").status_code == 403
    first_response = client.post(
        "/developer-data/grants",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    second_response = client.post(
        "/developer-data/grants",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert first_response.status_code == 201
    assert len(first_response.json()["code"].replace("-", "")) == 20
    assert second_response.status_code == 201
    old_exchange = Client(HTTP_HOST="localhost").post(
        "/developer-data/grants/exchange",
        data={
            "code": first_response.json()["code"],
            "bundle_version": "grant-replacement",
        },
        content_type="application/json",
    )
    assert old_exchange.status_code == 400
    current_grant = DeveloperDataDownloadGrant.objects.get(
        user__username="dev-data-grant",
        revoked_at__isnull=True,
    )
    current_grant.expires_at = timezone.now() - timedelta(seconds=1)
    current_grant.save(update_fields=["expires_at"])
    expired_exchange = Client(HTTP_HOST="localhost").post(
        "/developer-data/grants/exchange",
        data={
            "code": second_response.json()["code"],
            "bundle_version": "grant-replacement",
        },
        content_type="application/json",
    )
    assert expired_exchange.status_code == 400


def test_code_is_pinned_single_use_and_token_can_retry_until_expiry() -> None:
    content = _publish_test_bundle("token-retry")
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login(client, "dev-data-token")
    code_response = client.post(
        "/developer-data/grants",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    code = code_response.json()["code"]
    anonymous = Client(HTTP_HOST="localhost")

    unknown_response = anonymous.post(
        "/developer-data/grants/exchange",
        data={"code": code, "bundle_version": "not-published"},
        content_type="application/json",
    )
    exchange_response = anonymous.post(
        "/developer-data/grants/exchange",
        data={"code": code, "bundle_version": "token-retry"},
        content_type="application/json",
    )
    reused_response = anonymous.post(
        "/developer-data/grants/exchange",
        data={"code": code, "bundle_version": "token-retry"},
        content_type="application/json",
    )

    assert unknown_response.status_code == 404
    assert exchange_response.status_code == 200
    assert reused_response.status_code == 400
    token = exchange_response.json()["download_token"]
    for _attempt in range(2):
        response = anonymous.get(
            "/developer-data/bundles/token-retry/download",
            HTTP_AUTHORIZATION=f"DevData {token}",
        )
        assert response.status_code == 200
        response_body = b"".join(response.streaming_content)
        response.close()
        assert response_body == content

    grant = DeveloperDataDownloadGrant.objects.get(bundle_version="token-retry")
    set_developer_role(grant.user, enabled=False)
    role_revoked_response = anonymous.get(
        "/developer-data/bundles/token-retry/download",
        HTTP_AUTHORIZATION=f"DevData {token}",
    )
    assert role_revoked_response.status_code == 401
    set_developer_role(grant.user, enabled=True)
    grant.token_expires_at = timezone.now() - timedelta(seconds=1)
    grant.save(update_fields=["token_expires_at"])
    expired_response = anonymous.get(
        "/developer-data/bundles/token-retry/download",
        HTTP_AUTHORIZATION=f"DevData {token}",
    )
    assert expired_response.status_code == 401


def test_download_rechecks_user_activity_and_uses_internal_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    content = _publish_test_bundle("internal-redirect")
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login(client, "dev-data-accel")
    code = client.post(
        "/developer-data/grants",
        HTTP_X_CSRFTOKEN=csrf_token,
    ).json()["code"]
    anonymous = Client(HTTP_HOST="localhost")
    exchange = anonymous.post(
        "/developer-data/grants/exchange",
        data={"code": code, "bundle_version": "internal-redirect"},
        content_type="application/json",
    ).json()
    token = exchange["download_token"]
    monkeypatch.setattr(
        settings,
        "developer_data_accel_redirect_prefix",
        "/_internal/card-reader-dev-data/",
    )

    response = anonymous.get(
        "/developer-data/bundles/internal-redirect/download",
        HTTP_AUTHORIZATION=f"DevData {token}",
        HTTP_ACCEPT="application/gzip",
    )

    assert response.status_code == 200
    assert response.content == b""
    assert response["X-Accel-Redirect"] == (
        "/_internal/card-reader-dev-data/card-reader-dev-data-internal-redirect.tar.gz"
    )
    assert response["Content-Length"] == str(len(content))

    user = get_user_model().objects.get(username="dev-data-accel")
    user.is_active = False
    user.save(update_fields=["is_active"])
    denied_response = anonymous.get(
        "/developer-data/bundles/internal-redirect/download",
        HTTP_AUTHORIZATION=f"DevData {token}",
    )
    assert denied_response.status_code == 401


def test_production_download_refuses_to_fall_back_to_gunicorn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _publish_test_bundle("production-transfer")
    user = _create_user("dev-data-production-transfer", is_developer=True)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "developer_data_accel_redirect_prefix", "")

    response = client.get(
        "/developer-data/bundles/production-transfer/download",
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Protected developer-data transfer is not configured."


def test_staff_can_queue_and_list_builds_with_csrf() -> None:
    DeveloperDataBuild.objects.all().delete()
    regular = _create_user("dev-data-regular-builder")
    regular_client = Client(HTTP_HOST="localhost")
    regular_client.force_login(regular)
    staff_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login(staff_client, "dev-data-staff-builder", is_staff=True)

    assert regular_client.get("/developer-data/builds").status_code == 403
    assert regular_client.post("/developer-data/builds").status_code == 403
    assert staff_client.post("/developer-data/builds").status_code == 403

    create_response = staff_client.post(
        "/developer-data/builds",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    duplicate_response = staff_client.post(
        "/developer-data/builds",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    list_response = staff_client.get("/developer-data/builds")

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "queued"
    assert create_response.json()["requested_by"] == "dev-data-staff-builder"
    assert duplicate_response.status_code == 409
    assert list_response.status_code == 200
    assert list_response.json()["builds"][0]["id"] == create_response.json()["id"]


def test_staff_can_download_lock_file_for_successful_build() -> None:
    DeveloperDataBuild.objects.all().delete()
    staff = _create_user("dev-data-lock-builder", is_staff=True)
    client = Client(HTTP_HOST="localhost")
    client.force_login(staff)
    build = DeveloperDataBuild.objects.create(
        requested_by=staff,
        bundle_version="dev-lock-file",
        status=DeveloperDataBuildStatus.running,
    )
    artifact = PublishedBundle(
        bundle_version=build.bundle_version,
        format_version=1,
        filename="card-reader-dev-data-dev-lock-file.tar.gz",
        sha256="b" * 64,
        size_bytes=1234,
        created_at=timezone.now(),
    )
    mark_build_succeeded(build_id=build.id, artifact=artifact)

    response = client.get(f"/developer-data/builds/{build.id}/lock")

    assert response.status_code == 200
    assert response["Content-Disposition"] == 'attachment; filename="dev-data.lock.json"'
    assert response.json() == {
        "api_base_url": "https://maityscardgame.com/api",
        "bundle_version": "dev-lock-file",
        "format_version": 1,
        "sha256": "b" * 64,
    }


def test_build_worker_marks_success_and_recovers_already_published_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from card_reader_api.developer_data.build_worker import process_developer_data_build

    DeveloperDataBuild.objects.all().delete()
    staff = _create_user("dev-data-worker", is_staff=True)
    build = DeveloperDataBuild.objects.create(
        requested_by=staff,
        bundle_version="dev-worker",
        status=DeveloperDataBuildStatus.running,
    )
    artifact = PublishedBundle(
        bundle_version=build.bundle_version,
        format_version=1,
        filename="card-reader-dev-data-dev-worker.tar.gz",
        sha256="c" * 64,
        size_bytes=4321,
        created_at=timezone.now(),
    )
    published_root = tmp_path / "published"
    published_root.mkdir()
    monkeypatch.setattr(settings, "developer_data_dir", published_root)
    monkeypatch.setattr(
        "card_reader_api.developer_data.build_worker.PublishedBundleStore.get",
        lambda _store, _version: artifact,
    )

    process_developer_data_build(build)

    build.refresh_from_db()
    assert build.status == DeveloperDataBuildStatus.succeeded
    assert build.is_active_build is False
    assert build.sha256 == "c" * 64


def test_build_worker_adopts_bundle_published_by_concurrent_worker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from card_reader_api.developer_data.build_worker import _publish_or_adopt_existing

    artifact = PublishedBundle(
        bundle_version="dev-concurrent-worker",
        format_version=1,
        filename="card-reader-dev-data-dev-concurrent-worker.tar.gz",
        sha256="d" * 64,
        size_bytes=9876,
        created_at=timezone.now(),
    )
    store = PublishedBundleStore(root=tmp_path / "published")

    def already_published(_archive: Path) -> PublishedBundle:
        raise DeveloperDataError("already published")

    monkeypatch.setattr(
        store,
        "publish",
        already_published,
    )
    monkeypatch.setattr(store, "get", lambda _version: artifact)
    activated: list[PublishedBundle] = []
    monkeypatch.setattr(store, "activate", activated.append)

    result = _publish_or_adopt_existing(
        store=store,
        archive_path=tmp_path / "unused.tar.gz",
        bundle_version=artifact.bundle_version,
    )

    assert result == artifact
    assert activated == [artifact]


def test_build_completion_cannot_be_overwritten_by_late_failure() -> None:
    DeveloperDataBuild.objects.all().delete()
    staff = _create_user("dev-data-terminal-build", is_staff=True)
    build = DeveloperDataBuild.objects.create(
        requested_by=staff,
        bundle_version="dev-terminal-build",
        status=DeveloperDataBuildStatus.running,
    )
    artifact = PublishedBundle(
        bundle_version=build.bundle_version,
        format_version=1,
        filename="card-reader-dev-data-dev-terminal-build.tar.gz",
        sha256="e" * 64,
        size_bytes=321,
        created_at=timezone.now(),
    )

    mark_build_succeeded(build_id=build.id, artifact=artifact)
    mark_build_failed(build_id=build.id, error_message="late worker failure")

    build.refresh_from_db()
    assert build.status == DeveloperDataBuildStatus.succeeded
    assert build.error_message == ""


def test_build_recovery_only_requeues_stale_running_builds() -> None:
    DeveloperDataBuild.objects.all().delete()
    staff = _create_user("dev-data-stale-build", is_staff=True)
    stale = DeveloperDataBuild.objects.create(
        requested_by=staff,
        bundle_version="dev-stale-build",
        status=DeveloperDataBuildStatus.running,
    )
    fresh = DeveloperDataBuild.objects.create(
        requested_by=staff,
        bundle_version="dev-fresh-build",
        status=DeveloperDataBuildStatus.running,
        is_active_build=False,
    )
    DeveloperDataBuild.objects.filter(id=stale.id).update(
        updated_at=timezone.now() - timedelta(minutes=31)
    )

    assert requeue_interrupted_builds() == 1
    stale.refresh_from_db()
    fresh.refresh_from_db()
    assert stale.status == DeveloperDataBuildStatus.queued
    assert fresh.status == DeveloperDataBuildStatus.running


def test_builder_command_uses_shared_polling_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    from card_reader_core.operations.workers import WorkerShutdownController

    DeveloperDataBuild.objects.all().delete()
    _publish_test_bundle("shared-worker-command")
    staff = _create_user("dev-data-shared-worker", is_staff=True)
    build = DeveloperDataBuild.objects.create(
        requested_by=staff,
        bundle_version="shared-worker-command",
    )
    monkeypatch.setattr(
        WorkerShutdownController,
        "install_signal_handlers",
        lambda _controller: None,
    )

    call_command("run_dev_data_builder", "--once")

    build.refresh_from_db()
    assert build.status == DeveloperDataBuildStatus.succeeded


def _publish_test_bundle(version: str) -> bytes:
    root = settings.developer_data_root_dir
    root.mkdir(parents=True, exist_ok=True)
    filename = f"card-reader-dev-data-{version}.tar.gz"
    content = f"synthetic-public-bundle:{version}".encode()
    checksum = hashlib.sha256(content).hexdigest()
    metadata = {
        "bundle_version": version,
        "format_version": 1,
        "filename": filename,
        "sha256": checksum,
        "size_bytes": len(content),
        "created_at": timezone.now().isoformat(),
    }
    (root / filename).write_bytes(content)
    serialized = json.dumps(metadata)
    (root / f"{filename}.json").write_text(serialized, encoding="utf-8")
    (root / "current.json").write_text(serialized, encoding="utf-8")
    return content


def _create_user(  # type: ignore[no-untyped-def]
    username: str,
    *,
    is_active: bool = True,
    is_staff: bool = False,
    is_developer: bool = False,
):
    user_model = get_user_model()
    user_model.objects.filter(username=username).delete()
    user = user_model.objects.create_user(
        username=username,
        password="ValidPassword123!",
        is_active=is_active,
        is_staff=is_staff,
    )
    set_developer_role(user, enabled=is_developer)
    return user


def _login(client: Client, username: str, *, is_staff: bool = False) -> str:
    _create_user(username, is_staff=is_staff, is_developer=not is_staff)
    response = client.post(
        "/auth/login",
        data={"username": username, "password": "ValidPassword123!"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["can_download_developer_data"] is True
    assert response.json()["can_manage_developer_data"] is is_staff
    return str(response.json()["csrf_token"])

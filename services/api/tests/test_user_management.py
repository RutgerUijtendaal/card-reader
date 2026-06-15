from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.utils import timezone

from card_reader_core.models import (
    ACCESS_REQUEST_STATUS_APPROVED,
    ACCESS_REQUEST_STATUS_DECLINED,
    ACCESS_REQUEST_STATUS_PENDING,
    UserAccessRequest,
    UserActivity,
)


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_current_user_payload_includes_capabilities() -> None:
    username = "capability-staff-user"
    password = "password123!"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost")

    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["can_access_admin"] is True
    assert payload["can_manage_users"] is True
    assert payload["can_access_maintenance"] is False


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_create_list_archive_restore_and_reset_managed_users() -> None:
    username = "staff-user-manager"
    password = "password123!"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/admin/users",
        data={"username": "managed-viewer", "is_staff": True, "is_superuser": True},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert create_payload["user"]["username"] == "managed-viewer"
    assert create_payload["user"]["is_active"] is True
    created_user = get_user_model().objects.get(username="managed-viewer")
    assert created_user.is_staff is False
    assert created_user.is_superuser is False
    assert created_user.has_usable_password() is False

    list_response = client.get("/admin/users")
    assert list_response.status_code == 200
    listed_ids = {row["id"] for row in list_response.json()["managed_results"]}
    assert str(created_user.id) in listed_ids

    reset_response = client.post(
        f"/admin/users/{created_user.id}/reset-password",
        data={},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["user"]["id"] == str(created_user.id)

    archive_response = client.delete(
        f"/admin/users/{created_user.id}",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert archive_response.status_code == 204
    created_user.refresh_from_db()
    assert created_user.is_active is False

    active_list_response = client.get("/admin/users")
    active_ids = {row["id"] for row in active_list_response.json()["managed_results"]}
    assert str(created_user.id) not in active_ids

    archived_list_response = client.get("/admin/users", {"include_inactive": "true"})
    archived_ids = {row["id"] for row in archived_list_response.json()["managed_results"]}
    assert str(created_user.id) in archived_ids

    restore_response = client.post(
        f"/admin/users/{created_user.id}/restore",
        data={},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert restore_response.status_code == 200
    created_user.refresh_from_db()
    assert created_user.is_active is True


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_non_staff_cannot_access_user_management_endpoints() -> None:
    username = "regular-user-manager"
    password = "password123!"
    _create_user(username, password, is_staff=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.get("/admin/users", HTTP_X_CSRFTOKEN=csrf_token)

    assert response.status_code == 403


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_cannot_manage_privileged_accounts_through_managed_users_surface() -> None:
    username = "staff-privileged-guard"
    password = "password123!"
    _create_user(username, password, is_staff=True)
    privileged_user = _create_user(
        "staff-admin-target",
        "password123!",
        is_staff=True,
        is_superuser=True,
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    list_response = client.get("/admin/users")
    managed_usernames = {row["username"] for row in list_response.json()["managed_results"]}
    unmanaged_usernames = {row["username"] for row in list_response.json()["unmanaged_results"]}
    assert privileged_user.username not in managed_usernames
    assert privileged_user.username in unmanaged_usernames

    delete_response = client.delete(
        f"/admin/users/{privileged_user.id}",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert delete_response.status_code == 404
    privileged_user.refresh_from_db()
    assert privileged_user.is_active is True


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_authenticated_requests_record_last_active() -> None:
    user = _create_user("activity-tracked-user", "password123!", is_staff=False)
    UserActivity.objects.filter(user=user).delete()
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)

    response = client.get("/auth/me")

    assert response.status_code == 200
    activity = UserActivity.objects.get(user=user)
    assert activity.last_active_at is not None


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_only_superusers_can_see_last_activity_for_users() -> None:
    staff_username = "staff-unmanaged-viewer"
    superuser_username = "superuser-unmanaged-viewer"
    password = "password123!"
    _create_user(staff_username, password, is_staff=True)
    _create_user(superuser_username, password, is_staff=True, is_superuser=True)
    managed_user = _create_user("managed-last-active-target", password, is_staff=False)
    unmanaged_user = _create_user("staff-last-login-target", password, is_staff=True)
    managed_activity = timezone.now()
    unmanaged_activity = timezone.now()
    unmanaged_user.last_login = timezone.now()
    unmanaged_user.save(update_fields=["last_login"])
    UserActivity.objects.update_or_create(user=managed_user, defaults={"last_active_at": managed_activity})
    UserActivity.objects.update_or_create(user=unmanaged_user, defaults={"last_active_at": unmanaged_activity})

    staff_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    superuser_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    staff_csrf = _login_and_get_csrf_token(staff_client, staff_username, password)
    superuser_csrf = _login_and_get_csrf_token(superuser_client, superuser_username, password)

    staff_response = staff_client.get("/admin/users", HTTP_X_CSRFTOKEN=staff_csrf)
    superuser_response = superuser_client.get("/admin/users", HTTP_X_CSRFTOKEN=superuser_csrf)

    assert staff_response.status_code == 200
    assert superuser_response.status_code == 200

    staff_managed = {
        row["username"]: row for row in staff_response.json()["managed_results"]
    }["managed-last-active-target"]
    superuser_managed = {
        row["username"]: row for row in superuser_response.json()["managed_results"]
    }["managed-last-active-target"]
    staff_unmanaged = {
        row["username"]: row for row in staff_response.json()["unmanaged_results"]
    }["staff-last-login-target"]
    superuser_unmanaged = {
        row["username"]: row for row in superuser_response.json()["unmanaged_results"]
    }["staff-last-login-target"]

    assert staff_managed["last_active_at"] is None
    assert isinstance(superuser_managed["last_active_at"], str)
    assert staff_unmanaged["last_login"] is None
    assert staff_unmanaged["last_active_at"] is None
    assert isinstance(superuser_unmanaged["last_login"], str)
    assert isinstance(superuser_unmanaged["last_active_at"], str)


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_managed_user_can_set_password_once_and_then_only_access_public_routes() -> None:
    username = "staff-password-issuer"
    password = "password123!"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/admin/users",
        data={"username": "managed-login-user"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert create_response.status_code == 201
    create_payload = create_response.json()
    setup_values = _extract_setup_values(create_payload["setup_url"])

    invalid_response = client.post(
        "/auth/password/setup",
        data={**setup_values, "token": "invalid-token", "password": "ValidPassword123!"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert invalid_response.status_code == 400

    setup_response = client.post(
        "/auth/password/setup",
        data={**setup_values, "password": "ValidPassword123!"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert setup_response.status_code == 200

    reuse_response = client.post(
        "/auth/password/setup",
        data={**setup_values, "password": "AnotherValidPassword123!"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert reuse_response.status_code == 400

    managed_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    login_response = managed_client.post(
        "/auth/login",
        data={"username": "managed-login-user", "password": "ValidPassword123!"},
        content_type="application/json",
    )
    assert login_response.status_code == 200
    assert login_response.json()["can_access_admin"] is False

    assert managed_client.get("/cards").status_code == 200
    assert managed_client.get("/imports").status_code == 403


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_archived_user_cannot_log_in() -> None:
    user = _create_user("archived-login-user", "ValidPassword123!", is_staff=False)
    user.is_active = False
    user.save(update_fields=["is_active"])

    client = Client(HTTP_HOST="localhost")
    response = client.post(
        "/auth/login",
        data={"username": "archived-login-user", "password": "ValidPassword123!"},
        content_type="application/json",
    )

    assert response.status_code == 401


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_access_request_submission_deduplicates_pending_requests() -> None:
    UserAccessRequest.objects.filter(normalized_contact_handle="discord user").delete()
    client = Client(HTTP_HOST="localhost")

    response = client.post(
        "/auth/access-requests",
        data={"contact_handle": " Discord User ", "message": "I would like access."},
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["contact_handle"] == "Discord User"
    assert payload["message"] == "I would like access."
    assert payload["status"] == ACCESS_REQUEST_STATUS_PENDING

    duplicate_response = client.post(
        "/auth/access-requests",
        data={"contact_handle": "discord   user", "message": "Updated context."},
        content_type="application/json",
    )

    assert duplicate_response.status_code == 200
    duplicate_payload = duplicate_response.json()
    assert duplicate_payload["id"] == payload["id"]
    assert duplicate_payload["message"] == "Updated context."

    cleared_message_response = client.post(
        "/auth/access-requests",
        data={"contact_handle": "DISCORD USER", "message": ""},
        content_type="application/json",
    )

    assert cleared_message_response.status_code == 200
    assert cleared_message_response.json()["id"] == payload["id"]
    assert cleared_message_response.json()["message"] == ""
    assert (
        UserAccessRequest.objects.filter(
            normalized_contact_handle="discord user",
            status=ACCESS_REQUEST_STATUS_PENDING,
        ).count()
        == 1
    )


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_non_staff_cannot_access_access_request_admin_endpoints() -> None:
    username = "regular-access-request-manager"
    password = "password123!"
    _create_user(username, password, is_staff=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.get("/admin/access-requests", HTTP_X_CSRFTOKEN=csrf_token)

    assert response.status_code == 403


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_approve_access_request_and_issue_setup_link() -> None:
    staff_username = "staff-access-request-approver"
    password = "password123!"
    _create_user(staff_username, password, is_staff=True)
    request_record = UserAccessRequest.objects.create(
        contact_handle="Discord: requester",
        normalized_contact_handle="discord: requester",
        message="Please add me.",
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, staff_username, password)

    response = client.post(
        f"/admin/access-requests/{request_record.id}/approve",
        data={"username": "approved-request-user"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_request"]["status"] == ACCESS_REQUEST_STATUS_APPROVED
    assert payload["password_setup"]["user"]["username"] == "approved-request-user"
    created_user = get_user_model().objects.get(username="approved-request-user")
    assert created_user.is_staff is False
    assert created_user.is_superuser is False
    assert created_user.has_usable_password() is False
    request_record.refresh_from_db()
    assert request_record.status == ACCESS_REQUEST_STATUS_APPROVED
    assert request_record.created_user_id == created_user.id

    pending_response = client.get("/admin/access-requests", HTTP_X_CSRFTOKEN=csrf_token)
    assert pending_response.status_code == 200
    assert request_record.id not in {row["id"] for row in pending_response.json()}

    all_response = client.get(
        "/admin/access-requests",
        {"status": "all"},
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert all_response.status_code == 200
    assert request_record.id in {row["id"] for row in all_response.json()}


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_fetch_pending_access_request_summary() -> None:
    staff_username = "staff-access-request-summary"
    password = "password123!"
    _create_user(staff_username, password, is_staff=True)
    UserAccessRequest.objects.create(
        contact_handle="Pending Summary Handle",
        normalized_contact_handle="pending summary handle",
    )
    UserAccessRequest.objects.create(
        contact_handle="Resolved Summary Handle",
        normalized_contact_handle="resolved summary handle",
        status=ACCESS_REQUEST_STATUS_DECLINED,
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, staff_username, password)

    response = client.get("/admin/access-requests/summary", HTTP_X_CSRFTOKEN=csrf_token)

    assert response.status_code == 200
    assert response.json()["pending_access_request_count"] >= 1


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_decline_access_request_without_creating_user() -> None:
    staff_username = "staff-access-request-decliner"
    password = "password123!"
    _create_user(staff_username, password, is_staff=True)
    request_record = UserAccessRequest.objects.create(
        contact_handle="Handle To Decline",
        normalized_contact_handle="handle to decline",
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, staff_username, password)

    response = client.post(
        f"/admin/access-requests/{request_record.id}/decline",
        data={},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert response.json()["status"] == ACCESS_REQUEST_STATUS_DECLINED
    request_record.refresh_from_db()
    assert request_record.status == ACCESS_REQUEST_STATUS_DECLINED
    assert request_record.created_user_id is None


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_access_request_approval_username_conflict_keeps_request_pending() -> None:
    staff_username = "staff-access-request-conflict"
    password = "password123!"
    _create_user(staff_username, password, is_staff=True)
    _create_user("existing-request-user", password, is_staff=False)
    request_record = UserAccessRequest.objects.create(
        contact_handle="Conflict Handle",
        normalized_contact_handle="conflict handle",
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, staff_username, password)

    response = client.post(
        f"/admin/access-requests/{request_record.id}/approve",
        data={"username": "existing-request-user"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    request_record.refresh_from_db()
    assert request_record.status == ACCESS_REQUEST_STATUS_PENDING
    assert request_record.created_user_id is None


def _extract_setup_values(setup_url: str) -> dict[str, str]:
    parsed = urlparse(setup_url)
    query = parse_qs(parsed.query)
    return {
        "uid": query["uid"][0],
        "token": query["token"][0],
    }


def _create_user(
    username: str,
    password: str,
    *,
    is_staff: bool,
    is_superuser: bool = False,
):
    user_model = get_user_model()
    user_model.objects.filter(username=username).delete()
    user = user_model.objects.create_user(username=username, password=password)
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    user.save(update_fields=["is_staff", "is_superuser"])
    return user


def _login_and_get_csrf_token(client: Client, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    csrf_token = response.json()["csrf_token"]
    assert isinstance(csrf_token, str)
    return csrf_token

from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_STORAGE_ROOT = Path(tempfile.mkdtemp(prefix="card-reader-api-tests-"))
os.environ["CARD_READER_APP_DATA_DIR"] = str(TEST_STORAGE_ROOT)
os.environ["CARD_READER_ENV"] = "test"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")

import django  # noqa: E402
from card_reader_core.database.connection import initialize_database  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test import Client, override_settings  # noqa: E402

initialize_database()
django.setup()

from card_reader_api.seeds.users import seed_users  # noqa: E402

call_command("migrate", interactive=False, verbosity=0)
call_command("seed_defaults", verbosity=0)


def test_health() -> None:
    response = Client(HTTP_HOST="localhost").get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_create_import_upload_rejects_unknown_template() -> None:
    response = Client(HTTP_HOST="localhost").post(
        "/imports/upload",
        data={
            "template_id": "unknown-template",
            "options_json": "{}",
            "files": SimpleUploadedFile("card.png", b"fake-image-content", content_type="image/png"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown template_id 'unknown-template'"


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_create_import_upload_rejects_unsupported_files() -> None:
    response = Client(HTTP_HOST="localhost").post(
        "/imports/upload",
        data={"template_id": "mtg-like-v1", "options_json": "{}"},
    )
    assert response.status_code == 400


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_auth_enabled_keeps_card_gallery_public() -> None:
    client = Client(HTTP_HOST="localhost")

    assert client.get("/cards").status_code == 200
    assert client.get("/cards/filters").status_code == 200


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_auth_enabled_protects_non_gallery_routes() -> None:
    client = Client(HTTP_HOST="localhost")

    response = client.get("/imports")

    assert response.status_code in {401, 403}


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_auth_enabled_requires_staff_for_non_gallery_routes() -> None:
    staff_client = Client(HTTP_HOST="localhost")
    regular_client = Client(HTTP_HOST="localhost")
    staff_user = _create_user("staff-route-user", "password", is_staff=True)
    regular_user = _create_user("regular-route-user", "password", is_staff=False)
    staff_client.force_login(staff_user)
    regular_client.force_login(regular_user)

    assert staff_client.get("/imports").status_code == 200
    assert regular_client.get("/imports").status_code == 403


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_auth_enabled_requires_superuser_for_maintenance() -> None:
    staff_client = Client(HTTP_HOST="localhost")
    superuser_client = Client(HTTP_HOST="localhost")
    staff_user = _create_user("staff-maintenance-user", "password", is_staff=True)
    superuser = _create_user(
        "superuser-maintenance-user",
        "password",
        is_staff=True,
        is_superuser=True,
    )
    staff_client.force_login(staff_user)
    superuser_client.force_login(superuser)

    staff_response = staff_client.post(
        "/settings/maintenance/clear-storage",
        data={"include_images": False},
        content_type="application/json",
    )
    superuser_response = superuser_client.post(
        "/settings/maintenance/clear-storage",
        data={"include_images": False},
        content_type="application/json",
    )

    assert staff_response.status_code == 403
    assert superuser_response.status_code == 200


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_manage_catalog_entries() -> None:
    username = "staff-catalog-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    list_response = client.get("/settings/catalog")
    create_response = client.post(
        "/settings/keywords",
        data={"label": "Staff Catalog Keyword", "key": "staff-catalog-keyword"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert list_response.status_code == 200
    assert create_response.status_code == 200


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_manage_templates() -> None:
    username = "staff-template-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    list_response = client.get("/settings/templates")
    create_response = client.post(
        "/settings/templates",
        data={
            "label": "Staff Template",
            "key": "staff-template",
            "definition_json": "{}",
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert list_response.status_code == 200
    assert create_response.status_code == 200


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_logout_accepts_trusted_frontend_origin() -> None:
    username = "staff-logout-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost:8000", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/auth/logout",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 204


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_login_and_current_user() -> None:
    username = "auth-test-user"
    password = "auth-test-password"
    _create_user(username, password, is_staff=True)

    client = Client(HTTP_HOST="localhost")
    login_response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        content_type="application/json",
    )
    me_response = client.get("/auth/me")

    assert login_response.status_code == 200
    assert login_response.json()["authenticated"] is True
    assert login_response.json()["auth_enabled"] is True
    assert isinstance(login_response.json()["csrf_token"], str)
    assert login_response.json()["is_staff"] is True
    assert login_response.json()["is_superuser"] is False
    assert me_response.json()["username"] == username
    assert isinstance(me_response.json()["csrf_token"], str)


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_current_user_reports_unauthenticated_when_no_session() -> None:
    response = Client(HTTP_HOST="localhost").get("/auth/me")
    payload = response.json()

    assert response.status_code == 200
    assert payload["auth_enabled"] is True
    assert payload["authenticated"] is False
    assert isinstance(payload["csrf_token"], str)


def test_seed_users_creates_missing_configured_users(
    tmp_path: Path,
) -> None:
    seed_path = tmp_path / "seed-users.json"
    seed_path.write_text(
        """
        {
          "users": [
            {
              "username": "seed-user",
              "password": "seed-password",
              "is_staff": true,
              "is_superuser": true
            },
            {
              "username": "viewer-user",
              "password": "viewer-password",
              "is_staff": false
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    get_user_model().objects.filter(username__in=["seed-user", "viewer-user"]).delete()

    seed_users(seed_path)
    seed_users(seed_path)

    seed_user = get_user_model().objects.get(username="seed-user")
    viewer_user = get_user_model().objects.get(username="viewer-user")
    assert get_user_model().objects.filter(username__in=["seed-user", "viewer-user"]).count() == 2
    assert seed_user.check_password("seed-password")
    assert viewer_user.check_password("viewer-password")
    assert seed_user.is_staff is True
    assert seed_user.is_superuser is True
    assert viewer_user.is_staff is False
    assert viewer_user.is_superuser is False


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

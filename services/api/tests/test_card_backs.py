from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.models import CardBack
from card_reader_core.storage import resolve_storage_path


def _png_bytes(*, width: int = 7, height: int = 11) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(20, 40, 90)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def clear_card_backs() -> None:
    CardBack.objects.all().delete()


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_current_card_back_endpoint_returns_null_without_auth_when_unset() -> None:
    response = Client(HTTP_HOST="localhost").get("/card-backs/current")

    assert response.status_code == 200
    assert response.json() == {"current": None}


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_upload_creates_current_card_back_with_canonical_webp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    username = "staff-card-back-upload-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/admin/card-backs/upload",
        data={
            "label": "Blue Test Back",
            "file": SimpleUploadedFile("Blue Back.png", _png_bytes(), content_type="image/png"),
        },
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    payload = response.json()
    card_back = CardBack.objects.get()
    assert card_back.is_current is True
    assert card_back.label == "Blue Test Back"
    assert card_back.original_filename == "Blue Back.png"
    assert card_back.source_file.startswith("uploads/card-backs/blue-back-")
    assert card_back.stored_path == f"images/{card_back.checksum}.webp"
    assert card_back.width == 7
    assert card_back.height == 11
    assert resolve_storage_path(card_back.source_file).exists()
    assert resolve_storage_path(card_back.stored_path).exists()
    assert payload["id"] == card_back.id
    assert payload["is_current"] is True
    assert payload["image_url"] == f"/card-images/{card_back.stored_path}"

    current_response = client.get("/card-backs/current")
    assert current_response.status_code == 200
    current_payload = current_response.json()["current"]
    assert current_payload["id"] == card_back.id
    assert "source_file" not in current_payload
    assert "stored_path" not in current_payload
    assert "checksum" not in current_payload
    assert "original_filename" not in current_payload


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_upload_rejects_unreadable_card_back_and_cleans_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    username = "staff-card-back-invalid-upload-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/admin/card-backs/upload",
        data={
            "label": "Broken Back",
            "file": SimpleUploadedFile("broken.png", b"\x89PNG\r\n\x1a\nbroken", content_type="image/png"),
        },
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file must be a readable image."
    assert CardBack.objects.count() == 0
    upload_dir = resolve_storage_path("uploads/card-backs")
    assert not upload_dir.exists() or list(upload_dir.iterdir()) == []


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_activate_older_card_back() -> None:
    username = "staff-card-back-activate-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)
    first = _create_card_back(label="First Back", is_current=True, write_image=True)
    second = _create_card_back(label="Second Back", is_current=False, write_image=True)

    response = client.post(
        f"/admin/card-backs/{second.id}/activate",
        data={},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_current is False
    assert second.is_current is True
    assert response.json()["id"] == second.id
    assert response.json()["is_current"] is True


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_cannot_activate_card_back_with_missing_image() -> None:
    username = "staff-card-back-missing-image-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)
    current = _create_card_back(label="Current Back", is_current=True, write_image=True)
    missing = _create_card_back(label="Missing Back", is_current=False, write_image=False)

    response = client.post(
        f"/admin/card-backs/{missing.id}/activate",
        data={},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Card back image file is missing."
    current.refresh_from_db()
    missing.refresh_from_db()
    assert current.is_current is True
    assert missing.is_current is False


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_back_admin_endpoints_require_staff() -> None:
    client = Client(HTTP_HOST="localhost")
    regular_client = Client(HTTP_HOST="localhost")
    regular_user = _create_user("regular-card-back-user", "password", is_staff=False)
    regular_client.force_login(regular_user)
    card_back = _create_card_back(label="Protected Back", is_current=True, write_image=True)

    for method, path in [
        ("get", "/admin/card-backs"),
        ("post", "/admin/card-backs/upload"),
        ("post", f"/admin/card-backs/{card_back.id}/activate"),
    ]:
        assert getattr(client, method)(path).status_code in {401, 403}
        assert getattr(regular_client, method)(path).status_code == 403


def _create_user(
    username: str,
    password: str,
    *,
    is_staff: bool,
):
    user_model = get_user_model()
    user_model.objects.filter(username=username).delete()
    user = user_model.objects.create_user(username=username, password=password)
    user.is_staff = is_staff
    user.save(update_fields=["is_staff"])
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


def _create_card_back(*, label: str, is_current: bool, write_image: bool) -> CardBack:
    stored_path = f"images/{label}.webp"
    if write_image:
        image_path = resolve_storage_path(stored_path)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (63, 88), color=(20, 40, 90)).save(image_path, format="WEBP")
    return CardBack.objects.create(
        label=label,
        original_filename=f"{label}.png",
        source_file=f"uploads/card-backs/{label}.png",
        stored_path=stored_path,
        width=63,
        height=88,
        checksum=f"checksum-{label}",
        is_current=is_current,
    )

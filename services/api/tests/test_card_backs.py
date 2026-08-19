from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.models import Card, CardBack, CardBackPoolDefault, CardVersion, Template
from card_reader_core.storage import resolve_storage_path


def _png_bytes(*, width: int = 7, height: int = 11) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(20, 40, 90)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_public_defaults_always_return_all_pools_and_current_aliases_player() -> None:
    card_back = _create_card_back(label="Player Back", write_image=True)
    CardBackPoolDefault.objects.create(card_pool="player", card_back=card_back)

    defaults_response = Client(HTTP_HOST="localhost").get("/card-backs/defaults")
    current_response = Client(HTTP_HOST="localhost").get("/card-backs/current")

    assert defaults_response.status_code == 200
    assert defaults_response.json() == {
        "player": current_response.json()["current"],
        "evil": None,
        "neutral": None,
    }
    assert current_response.json()["current"]["id"] == card_back.id


@override_settings(DEBUG=True)
def test_pool_default_update_cors_preflight_allows_put() -> None:
    origin = "http://localhost:8888"

    response = Client(HTTP_HOST="localhost").options(
        "/admin/card-backs/defaults/player",
        HTTP_ORIGIN=origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="PUT",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,x-csrftoken",
    )

    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == origin
    allowed_methods = response["Access-Control-Allow-Methods"].split(",")
    assert "PUT" in allowed_methods


def test_immutable_card_back_asset_supports_non_checksum_filename() -> None:
    card_back = _create_card_back(label="Legacy Named Back", write_image=True)

    response = Client(HTTP_HOST="localhost").get(f"/card-images/{card_back.stored_path}")

    assert response.status_code == 200
    assert b"".join(response.streaming_content).startswith(b"RIFF")
    response.close()


def test_staff_upload_creates_unassigned_asset_with_canonical_webp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    client, csrf_token = _staff_client("staff-card-back-upload-user")

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
    assert CardBackPoolDefault.objects.count() == 0
    assert card_back.label == "Blue Test Back"
    assert card_back.source_file.startswith("uploads/card-backs/blue-back-")
    assert card_back.stored_path == f"images/{card_back.checksum}.webp"
    assert resolve_storage_path(card_back.source_file).exists()
    assert resolve_storage_path(card_back.stored_path).exists()
    assert payload["default_for_pools"] == []
    assert payload["override_card_count"] == 0
    assert payload["is_usable"] is True
    assert client.get("/card-backs/current").json() == {"current": None}


def test_staff_upload_rejects_unreadable_card_back_and_cleans_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    client, csrf_token = _staff_client("staff-card-back-invalid-upload-user")

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


def test_staff_sets_one_pool_default_without_changing_other_pools() -> None:
    client, csrf_token = _staff_client("staff-card-back-default-user")
    first = _create_card_back(label="First Back", write_image=True)
    second = _create_card_back(label="Second Back", write_image=True)
    CardBackPoolDefault.objects.create(card_pool="player", card_back=first)

    response = client.put(
        "/admin/card-backs/defaults/evil",
        data={"card_back_id": second.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert CardBackPoolDefault.objects.get(card_pool="player").card_back_id == first.id
    assert CardBackPoolDefault.objects.get(card_pool="evil").card_back_id == second.id


def test_staff_clears_one_pool_default_without_changing_other_pools() -> None:
    client, csrf_token = _staff_client("staff-card-back-clear-default-user")
    card_back = _create_card_back(label="Shared Back", write_image=True)
    CardBackPoolDefault.objects.bulk_create(
        [
            CardBackPoolDefault(card_pool="player", card_back=card_back),
            CardBackPoolDefault(card_pool="evil", card_back=card_back),
        ]
    )

    response = client.put(
        "/admin/card-backs/defaults/evil",
        data={"card_back_id": None},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert response.json() is None
    assert CardBackPoolDefault.objects.get(card_pool="player").card_back_id == card_back.id
    assert not CardBackPoolDefault.objects.filter(card_pool="evil").exists()


def test_staff_cannot_assign_card_back_with_missing_image() -> None:
    client, csrf_token = _staff_client("staff-card-back-missing-image-user")
    missing = _create_card_back(label="Missing Back", write_image=False)

    response = client.put(
        "/admin/card-backs/defaults/neutral",
        data={"card_back_id": missing.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Card back image file is missing."
    assert not CardBackPoolDefault.objects.filter(card_pool="neutral").exists()


def test_admin_list_reports_default_and_override_usage() -> None:
    client, _csrf_token = _staff_client("staff-card-back-list-user")
    card_back = _create_card_back(label="Used Back", write_image=True)
    CardBackPoolDefault.objects.create(card_pool="player", card_back=card_back)
    Card.objects.create(key="card", label="Card", card_back_override=card_back)

    response = client.get("/admin/card-backs")

    assert response.status_code == 200
    assert response.json()[0]["default_for_pools"] == ["player"]
    assert response.json()[0]["override_card_count"] == 1


def test_card_patch_sets_and_clears_override_inside_the_card_edit() -> None:
    client, csrf_token = _staff_client("staff-card-back-card-edit-user")
    inherited = _create_card_back(label="Evil Default", write_image=True)
    override = _create_card_back(label="Card Override", write_image=True)
    CardBackPoolDefault.objects.create(card_pool="evil", card_back=inherited)
    template = Template.objects.create(key="card-back-edit", label="Card Back Edit")
    card = Card.objects.create(key="card-back-edit", label="Card Back Edit")
    version = CardVersion.objects.create(
        card=card,
        template=template,
        image_hash="card-back-edit-hash",
        name="Card Back Edit",
    )
    card.latest_version = version
    card.save(update_fields=["latest_version"])
    original_updated_at = card.updated_at

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"card_pool": "evil", "card_back_override_id": override.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    card.refresh_from_db()
    assert card.card_pool == "evil"
    assert card.card_back_override_id == override.id
    assert card.updated_at > original_updated_at
    assert response.json()["effective_card_back"]["source"] == "override"

    clear_response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"card_back_override_id": None},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert clear_response.status_code == 200
    card.refresh_from_db()
    assert card.card_back_override_id is None
    assert clear_response.json()["effective_card_back"]["source"] == "pool_default"
    assert clear_response.json()["effective_card_back"]["asset"]["id"] == inherited.id


def test_invalid_card_override_keeps_the_rest_of_the_card_edit_unchanged() -> None:
    client, csrf_token = _staff_client("staff-card-back-atomic-user")
    template = Template.objects.create(key="card-back-atomic", label="Card Back Atomic")
    card = Card.objects.create(key="card-back-atomic", label="Card Back Atomic")
    version = CardVersion.objects.create(
        card=card,
        template=template,
        image_hash="card-back-atomic-hash",
        name="Card Back Atomic",
    )
    card.latest_version = version
    card.save(update_fields=["latest_version"])

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"card_pool": "evil", "card_back_override_id": "missing-card-back"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    card.refresh_from_db()
    assert card.card_pool == "player"
    assert card.card_back_override_id is None


def test_card_back_admin_endpoints_require_staff() -> None:
    anonymous = Client(HTTP_HOST="localhost")
    regular = Client(HTTP_HOST="localhost")
    regular.force_login(_create_user("regular-card-back-user", "password", is_staff=False))

    for method, path in [
        ("get", "/admin/card-backs"),
        ("post", "/admin/card-backs/upload"),
        ("put", "/admin/card-backs/defaults/player"),
    ]:
        assert getattr(anonymous, method)(path).status_code in {401, 403}
        assert getattr(regular, method)(path).status_code == 403


def _staff_client(username: str) -> tuple[Client, str]:
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    return client, _login_and_get_csrf_token(client, username, password)


def _create_user(username: str, password: str, *, is_staff: bool):
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
    return str(response.json()["csrf_token"])


def _create_card_back(*, label: str, write_image: bool) -> CardBack:
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
    )

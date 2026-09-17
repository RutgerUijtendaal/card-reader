from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    Card,
    CardBack,
    CardBackImportReceipt,
    CardBackFactionDefault,
    CardBackPoolDefault,
    CardBackRoleDefault,
    CardFactionAssignment,
    CardRoleAssignment,
    CardVersion,
    Template,
)
from card_reader_core.storage import resolve_storage_path
from card_reader_core.services.card_backs import resolve_effective_card_backs


def _import_hero(*, pool: str = "player", override: CardBack | None = None) -> Card:
    card = Card.objects.create(key=str(uuid4()), label="Import Hero", card_pool=pool, card_back_override=override)
    template = Template.objects.first()
    version = CardVersion.objects.create(card=card, template=template, image_hash=str(uuid4()), name="Import Hero")
    card.latest_version = version
    card.save(update_fields=["latest_version"])
    CardRoleAssignment.objects.create(card=card, role="hero")
    return card


def _import_row(client: Client, csrf: str, key: str, **fields: object):
    return client.post(
        "/admin/card-backs/import-items",
        data={
            "client_request_id": key, "label": "Hero back",
            "file": SimpleUploadedFile("hero.png", _png_bytes(), content_type="image/png"),
            **fields,
        },
        HTTP_X_CSRFTOKEN=csrf,
    )


def test_import_unassigned_asset_replays_before_body_validation_and_survives_deletion() -> None:
    client, csrf = _staff_client("import-library")
    key = str(uuid4())
    first = _import_row(client, csrf, key)
    assert first.status_code == 201
    assert first.json()["outcome"] == "succeeded"
    assert first.json()["hero_card_id"] is None
    assert not CardBackPoolDefault.objects.exists()
    assert not CardBackRoleDefault.objects.exists()
    assert not CardBackFactionDefault.objects.exists()
    replay = client.post("/admin/card-backs/import-items", data={"client_request_id": key}, HTTP_X_CSRFTOKEN=csrf)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert CardBack.objects.count() == 1
    CardBack.objects.get().delete()
    deleted = _import_row(client, csrf, key)
    assert deleted.json()["outcome"] == "deleted"
    assert CardBack.objects.count() == 0
    assert CardBackImportReceipt.objects.count() == 1


@pytest.mark.parametrize("pool", ["player", "evil", "neutral"])
def test_import_assigns_hero_across_pools_without_changing_defaults(pool: str) -> None:
    client, csrf = _staff_client("import-hero")
    previous = _create_card_back(label="previous", write_image=True)
    CardBackPoolDefault.objects.create(card_pool=pool, card_back=previous)
    hero = _import_hero(pool=pool, override=previous)
    key = str(uuid4())
    result = _import_row(client, csrf, key, hero_card_id=hero.id, expected_override_id=previous.id)
    assert result.json()["outcome"] == "succeeded"
    hero.refresh_from_db()
    new_back_id = result.json()["asset"]["id"]
    assert hero.card_back_override_id == new_back_id
    assert CardBack.objects.filter(id=previous.id).exists()
    assert CardBackPoolDefault.objects.get(card_pool=pool).card_back_id == previous.id
    resolved = resolve_effective_card_backs([hero.id])[hero.id]
    assert resolved.source == "override"
    assert resolved.card_back is not None
    assert resolved.card_back.id == new_back_id

    # A lost-response retry must not undo a later staff edit.
    hero.card_back_override = previous
    hero.save(update_fields=["card_back_override"])
    replay = _import_row(client, csrf, key, hero_card_id=hero.id, expected_override_id=previous.id)
    hero.refresh_from_db()
    assert replay.json()["asset"]["id"] == new_back_id
    assert hero.card_back_override_id == previous.id
    lookup = client.get(f"/admin/card-backs/import-items/{key}")
    assert lookup.json() == replay.json()
    assert CardBack.objects.count() == 2


def test_import_null_override_from_multipart_is_supported() -> None:
    client, csrf = _staff_client("import-empty-override")
    hero = _import_hero()
    result = _import_row(client, csrf, str(uuid4()), hero_card_id=hero.id, expected_override_id="")
    assert result.json()["outcome"] == "succeeded"
    hero.refresh_from_db()
    assert hero.card_back_override_id == result.json()["asset"]["id"]


@pytest.mark.parametrize("invalid", ["stale", "deprecated", "not_hero", "deleted"])
def test_import_rejects_changed_hero_atomically_and_records_terminal_rejection(invalid: str) -> None:
    client, csrf = _staff_client("import-conflict")
    previous = _create_card_back(label="previous", write_image=True)
    hero = _import_hero(override=previous)
    hero_id = hero.id
    expected = previous.id
    if invalid == "stale":
        expected = ""
    elif invalid == "deprecated":
        hero.lifecycle_status = "deprecated"
        hero.save(update_fields=["lifecycle_status"])
    elif invalid == "not_hero":
        hero.role_assignments.all().delete()
    else:
        hero.delete()
    key = str(uuid4())
    response = _import_row(client, csrf, key, hero_card_id=hero_id, expected_override_id=expected)
    assert response.json()["outcome"] == "rejected"
    assert CardBack.objects.count() == 1
    assert not list(resolve_storage_path("uploads/card-backs").glob("*"))
    # Repairing/changing the hero cannot make the same key execute later.
    replay = _import_row(client, csrf, key)
    assert replay.json() == response.json()
    assert CardBack.objects.count() == 1
    assert CardBackImportReceipt.objects.get().error


@pytest.mark.parametrize("fields", [
    {"label": " "},
    {"file": SimpleUploadedFile("broken.png", b"not an image")},
    {"hero_card_id": "missing", "expected_override_id": ""},
])
def test_import_invalid_rows_do_not_create_assets(fields: dict[str, object]) -> None:
    client, csrf = _staff_client("import-invalid")
    response = _import_row(client, csrf, str(uuid4()), **fields)
    assert response.status_code == 400 or response.json()["outcome"] == "rejected"
    assert not CardBack.objects.exists()


def test_import_requires_explicit_expected_override() -> None:
    client, csrf = _staff_client("import-missing-expectation")
    hero = _import_hero()
    response = _import_row(client, csrf, str(uuid4()), hero_card_id=hero.id)
    assert response.status_code == 400
    assert not CardBack.objects.exists()


def test_import_receipts_are_owner_scoped_and_staff_csrf_protected() -> None:
    first, csrf = _staff_client("import-first")
    key = str(uuid4())
    assert _import_row(first, csrf, key).status_code == 201
    second, second_csrf = _staff_client("import-second")
    assert second.get(f"/admin/card-backs/import-items/{key}").status_code == 404
    assert _import_row(second, "", str(uuid4())).status_code == 403
    assert _import_row(second, second_csrf, key).status_code == 201
    assert CardBack.objects.count() == 2
    anonymous = Client(HTTP_HOST="localhost")
    assert anonymous.get(f"/admin/card-backs/import-items/{key}").status_code == 403
    assert _import_row(anonymous, "", str(uuid4())).status_code == 403
    _create_user("ordinary-importer", "password", is_staff=False)
    ordinary = Client(HTTP_HOST="localhost")
    ordinary.force_login(get_user_model().objects.get(username="ordinary-importer"))
    assert _import_row(ordinary, "", str(uuid4())).status_code == 403


def test_import_unexpected_assignment_failure_rolls_back_asset_and_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    from card_reader_core.services.cards import card_back_imports
    client, csrf = _staff_client("import-rollback")
    hero = _import_hero()

    def fail(**_kwargs: object) -> None:
        raise RuntimeError("unexpected assignment failure")

    monkeypatch.setattr(card_back_imports, "update_latest_card_version_with_notifications", fail)
    with pytest.raises(RuntimeError, match="unexpected assignment"):
        _import_row(client, csrf, str(uuid4()), hero_card_id=hero.id, expected_override_id="")
    assert not CardBack.objects.exists()
    assert not CardBackImportReceipt.objects.exists()
    hero.refresh_from_db()
    assert hero.card_back_override_id is None
    assert not list(resolve_storage_path("uploads/card-backs").glob("*"))


@pytest.mark.django_db(transaction=True)
def test_concurrent_import_requests_create_one_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from django.db import OperationalError, close_old_connections
    from card_reader_core.services.cards import card_back_imports

    user = _create_user("import-race", "password", is_staff=True)
    key = uuid4()
    barrier = Barrier(2)
    prepare = card_back_imports.prepare_card_back_asset

    def synchronized_prepare(**kwargs):
        prepared = prepare(**kwargs)
        barrier.wait(timeout=10)
        return prepared

    monkeypatch.setattr(card_back_imports, "prepare_card_back_asset", synchronized_prepare)

    def run():
        close_old_connections()
        try:
            receipt, _created = card_back_imports.import_card_back(
                owner_id=str(user.pk), client_request_id=key, filename="race.png",
                chunks=[_png_bytes()], label="Race", hero_card_id=None, expected_override_id=None,
            )
            return receipt.card_back_id
        except OperationalError as exc:
            # Shared in-memory SQLite can report busy instead of waiting for the writer.
            if "locked" not in str(exc):
                raise
            return None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run), executor.submit(run)]
        results = [future.result(timeout=20) for future in futures]
    monkeypatch.setattr(card_back_imports, "prepare_card_back_asset", prepare)
    results = [result if result is not None else run() for result in results]
    assert results[0] == results[1]
    assert CardBack.objects.count() == 1
    assert CardBackImportReceipt.objects.count() == 1
    assert len(list(resolve_storage_path("uploads/card-backs").glob("*"))) == 1


def test_import_cleanup_failure_preserves_terminal_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    from card_reader_core.services.card_backs import assets
    client, csrf = _staff_client("import-cleanup")
    hero = _import_hero()
    hero.role_assignments.all().delete()
    original_unlink = Path.unlink

    def fail_source_unlink(path: Path, *args, **kwargs):
        if "card-backs" in path.parts:
            raise OSError("cleanup unavailable")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(assets.Path, "unlink", fail_source_unlink)
    key = str(uuid4())
    response = _import_row(client, csrf, key, hero_card_id=hero.id, expected_override_id="")
    assert response.json()["outcome"] == "rejected"
    assert client.get(f"/admin/card-backs/import-items/{key}").json() == response.json()
    assert not CardBack.objects.exists()


def test_import_receipts_are_not_developer_data() -> None:
    from card_reader_core.operations.developer_data.exporter import _build_payload
    client, csrf = _staff_client("import-private-receipt")
    _import_row(client, csrf, str(uuid4()))
    payload = _build_payload(cards=[], groups=[]).model_dump(mode="json")
    assert "card_back_import_receipts" not in payload
    assert "import_receipts" not in payload
    assert "client_request_id" not in str(payload)


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


def test_public_faction_defaults_always_return_every_evil_faction() -> None:
    card_back = _create_card_back(label="Order Back", write_image=True)
    CardBackFactionDefault.objects.create(faction="order", card_back=card_back)

    response = Client(HTTP_HOST="localhost").get("/card-backs/faction-defaults")

    assert response.status_code == 200
    assert response.json() == {
        "order": {
            "id": card_back.id,
            "label": card_back.label,
            "width": card_back.width,
            "height": card_back.height,
            "image_url": f"/card-images/{card_back.stored_path}",
            "created_at": card_back.created_at.isoformat(),
            "updated_at": card_back.updated_at.isoformat(),
        },
        "blood": None,
        "dark": None,
        "metal": None,
        "fire": None,
    }


def test_public_role_defaults_always_return_every_persisted_role() -> None:
    card_back = _create_card_back(label="Hero Back", write_image=True)
    CardBackRoleDefault.objects.create(role="hero", card_back=card_back)

    response = Client(HTTP_HOST="localhost").get("/card-backs/role-defaults")

    assert response.status_code == 200
    assert response.json() == {
        "hero": {
            "id": card_back.id,
            "label": card_back.label,
            "width": card_back.width,
            "height": card_back.height,
            "image_url": f"/card-images/{card_back.stored_path}",
            "created_at": card_back.created_at.isoformat(),
            "updated_at": card_back.updated_at.isoformat(),
        },
        "boss": None,
        "location": None,
        "boon": None,
        "event": None,
        "shop_item": None,
        "directive": None,
        "reminder": None,
        "mana": None,
    }


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

    assert response.status_code == 204
    assert response.content == b""
    assert CardBackPoolDefault.objects.get(card_pool="player").card_back_id == card_back.id
    assert not CardBackPoolDefault.objects.filter(card_pool="evil").exists()


def test_staff_sets_and_clears_one_faction_default() -> None:
    client, csrf_token = _staff_client("staff-card-back-faction-default-user")
    card_back = _create_card_back(label="Blood Back", write_image=True)

    response = client.put(
        "/admin/card-backs/faction-defaults/blood",
        data={"card_back_id": card_back.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert CardBackFactionDefault.objects.get(faction="blood").card_back_id == card_back.id

    clear_response = client.put(
        "/admin/card-backs/faction-defaults/blood",
        data={"card_back_id": None},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert clear_response.status_code == 204
    assert not CardBackFactionDefault.objects.filter(faction="blood").exists()


def test_staff_sets_and_clears_one_role_default() -> None:
    client, csrf_token = _staff_client("staff-card-back-role-default-user")
    card_back = _create_card_back(label="Boss Back", write_image=True)

    response = client.put(
        "/admin/card-backs/role-defaults/boss",
        data={"card_back_id": card_back.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert CardBackRoleDefault.objects.get(role="boss").card_back_id == card_back.id

    clear_response = client.put(
        "/admin/card-backs/role-defaults/boss",
        data={"card_back_id": None},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert clear_response.status_code == 204
    assert not CardBackRoleDefault.objects.filter(role="boss").exists()


def test_staff_role_default_rejects_invalid_role_and_unusable_asset() -> None:
    client, csrf_token = _staff_client("staff-card-back-invalid-role-default-user")
    usable = _create_card_back(label="Usable Back", write_image=True)
    missing = _create_card_back(label="Missing Back", write_image=False)

    invalid_role_response = client.put(
        "/admin/card-backs/role-defaults/standard",
        data={"card_back_id": usable.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    missing_asset_response = client.put(
        "/admin/card-backs/role-defaults/hero",
        data={"card_back_id": missing.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert invalid_role_response.status_code == 400
    assert invalid_role_response.json()["detail"] == "Invalid card role."
    assert missing_asset_response.status_code == 400
    assert missing_asset_response.json()["detail"] == "Card back image file is missing."
    assert CardBackRoleDefault.objects.count() == 0


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
    CardBackFactionDefault.objects.create(faction="fire", card_back=card_back)
    CardBackRoleDefault.objects.create(role="event", card_back=card_back)
    Card.objects.create(key="card", label="Card", card_back_override=card_back)

    response = client.get("/admin/card-backs")

    assert response.status_code == 200
    assert response.json()[0]["default_for_pools"] == ["player"]
    assert response.json()[0]["default_for_factions"] == ["fire"]
    assert response.json()[0]["default_for_roles"] == ["event"]
    assert response.json()[0]["override_card_count"] == 1


def test_card_patch_sets_and_clears_override_inside_the_card_edit() -> None:
    client, csrf_token = _staff_client("staff-card-back-card-edit-user")
    inherited = _create_card_back(label="Evil Default", write_image=True)
    override = _create_card_back(label="Card Override", write_image=True)
    faction_default = _create_card_back(label="Order Default", write_image=True)
    CardBackPoolDefault.objects.create(card_pool="evil", card_back=inherited)
    CardBackFactionDefault.objects.create(faction="order", card_back=faction_default)
    role_default = _create_card_back(label="Event Default", write_image=True)
    CardBackRoleDefault.objects.create(role="event", card_back=role_default)
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
    CardFactionAssignment.objects.create(card=card, faction="order")
    CardRoleAssignment.objects.create(card=card, role="event")
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
    assert clear_response.json()["effective_card_back"]["source"] == "role_default"
    assert clear_response.json()["effective_card_back"]["role"] == "event"
    assert clear_response.json()["effective_card_back"]["asset"]["id"] == role_default.id


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
        ("put", "/admin/card-backs/faction-defaults/order"),
        ("put", "/admin/card-backs/role-defaults/hero"),
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

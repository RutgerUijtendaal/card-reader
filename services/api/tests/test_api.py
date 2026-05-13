import json
from pathlib import Path
from types import SimpleNamespace

from card_reader_core.models import Card, CardVersion, CardVersionImage, ImportJob, ImportJobItem, Keyword, ParseResult, Symbol, Tag, Type  # noqa: E402
from card_reader_core.repositories.cards_repository import get_latest_card_version  # noqa: E402
from card_reader_core.repositories.import_jobs_repository import create_import_job_with_files  # noqa: E402
from card_reader_core.repositories.metadata_repository import (  # noqa: E402
    get_tags_for_card_version,
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
)
from card_reader_core.services.imports import ImportService  # noqa: E402
from card_reader_core.services.parser_jobs import ImportProcessorService  # noqa: E402
from card_reader_core.settings import settings  # noqa: E402
from card_reader_core.storage import build_storage_relative_path, relativize_image_storage_path, resolve_storage_path  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.test import Client, override_settings  # noqa: E402

from card_reader_api.seeds.users import seed_users  # noqa: E402


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


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_create_import_upload_stores_relative_paths() -> None:
    response = Client(HTTP_HOST="localhost").post(
        "/imports/upload",
        data={
            "template_id": "mtg-like-v1",
            "options_json": "{}",
            "files": SimpleUploadedFile("card.png", b"fake-image-content", content_type="image/png"),
        },
    )

    assert response.status_code == 201
    job = ImportJob.objects.get(id=response.json()["id"])
    item = ImportJobItem.objects.get(job_id=job.id)
    assert job.source_path.startswith("uploads/")
    assert item.source_file.startswith(f"{job.source_path}/")


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_cancel_queued_import_job_marks_it_cancelled() -> None:
    job = ImportJob.objects.create(
        source_path="uploads/test-job",
        template_id="mtg-like-v1",
        options_json={},
        total_items=2,
        processed_items=0,
    )
    ImportJobItem.objects.create(job=job, source_file="uploads/test-job/0001.png")
    ImportJobItem.objects.create(job=job, source_file="uploads/test-job/0002.png")

    response = Client(HTTP_HOST="localhost").post(f"/imports/{job.id}/cancel", data={}, content_type="application/json")

    assert response.status_code == 202
    job.refresh_from_db()
    assert job.status == "cancelled"
    assert job.processed_items == 2
    assert list(ImportJobItem.objects.filter(job_id=job.id).values_list("status", flat=True)) == [
        "cancelled",
        "cancelled",
    ]


def test_processor_honors_running_job_cancellation_after_current_item() -> None:
    image_one = settings.storage_root_dir / "uploads" / "interrupt-job" / "0001.png"
    image_two = settings.storage_root_dir / "uploads" / "interrupt-job" / "0002.png"
    image_one.parent.mkdir(parents=True, exist_ok=True)
    image_one.write_bytes(b"image-one")
    image_two.write_bytes(b"image-two")

    job = create_import_job_with_files(
        source_path=image_one.parent,
        template_id="mtg-like-v1",
        options={},
        files=[image_one, image_two],
    )

    class InterruptingParser:
        def __init__(self) -> None:
            self.call_count = 0

        def parse(self, image_path: Path, template_id: str, **_: object) -> SimpleNamespace:
            self.call_count += 1
            if self.call_count == 1:
                ImportService().cancel_job(job_id=job.id)
            return SimpleNamespace(
                checksum=f"checksum-{self.call_count}",
                normalized_fields={
                    "name": f"Interrupt Test {self.call_count}",
                    "type_line": "Type",
                    "mana_cost": "",
                    "attack": "",
                    "health": "",
                    "rules_text": "",
                },
                confidence={"overall": 0.9},
                raw_ocr={"source": str(image_path), "template_id": template_id},
                keyword_ids=[],
                tag_ids=[],
                type_ids=[],
                symbol_ids=[],
            )

    processor = ImportProcessorService(InterruptingParser())
    processor.process_job(job.id)

    job.refresh_from_db()
    items = list(ImportJobItem.objects.filter(job_id=job.id).order_by("created_at"))
    assert job.status == "cancelled"
    assert job.processed_items == 2
    assert [item.status for item in items] == ["completed", "cancelled"]


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
def test_staff_can_create_keyword_identifiers() -> None:
    username = "staff-keyword-alias-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/settings/keywords",
        data={
            "label": "Turn Start",
            "key": "turn-start-alias-test",
            "identifiers": ["At the beginning of your turn", "  TURN START  "],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert response.json()["identifiers"] == ["turn start", "at the beginning of your turn"]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_create_tag_and_type_identifiers() -> None:
    username = "staff-tag-type-identifiers-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    tag_response = client.post(
        "/settings/tags",
        data={
            "label": "Weapon",
            "key": "weapon-identifiers-test",
            "identifiers": ["arms", "  WEAPON  "],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    type_response = client.post(
        "/settings/types",
        data={
            "label": "Persistent",
            "key": "persistent-identifiers-test",
            "identifiers": ["ongoing", "  PERSISTENT  "],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert tag_response.status_code == 200
    assert tag_response.json()["identifiers"] == ["weapon", "arms"]
    assert type_response.status_code == 200
    assert type_response.json()["identifiers"] == ["persistent", "ongoing"]


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


def test_cards_list_returns_paginated_payload() -> None:
    first_card, first_version = _create_editable_card_version(name="Paged One")
    second_card, second_version = _create_editable_card_version(name="Paged Two")
    _create_card_image(first_version)
    _create_card_image(second_version)

    response = Client(HTTP_HOST="localhost").get("/cards")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 2
    assert payload["page"] == 1
    assert payload["page_size"] == 72
    assert payload["previous_page"] is None
    assert isinstance(payload["results"], list)
    result_ids = {row["id"] for row in payload["results"]}
    assert first_card.id in result_ids
    assert second_card.id in result_ids


def test_card_gallery_image_endpoint_serves_latest_image(tmp_path: Path) -> None:
    card, version = _create_editable_card_version(name="Image Card")
    image_path = settings.image_store_dir / f"checksum-{version.id}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"fake-image")
    CardVersionImage.objects.create(
        card_version=version,
        source_file=build_storage_relative_path("images", image_path.name),
        stored_path=build_storage_relative_path("images", image_path.name),
        checksum=f"checksum-{version.id}",
    )

    response = Client(HTTP_HOST="localhost").get(f"/cards/{card.id}/image")

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"fake-image"


def test_storage_paths_resolve_relative_to_storage_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)

    resolved = resolve_storage_path("images/example-card.png")
    from_dev_absolute = relativize_image_storage_path(str(tmp_path / "images" / "example-card.png"))
    from_prd_absolute = relativize_image_storage_path("/var/lib/card-reader/images/example-card.png")

    assert resolved == tmp_path / "images" / "example-card.png"
    assert from_dev_absolute == "images/example-card.png"
    assert from_prd_absolute == "images/example-card.png"


def test_cards_list_pagination_honors_page_and_page_size() -> None:
    created = []
    for index in range(3):
        card, version = _create_editable_card_version(name=f"Page Card {index}")
        _create_card_image(version)
        created.append(card.id)

    client = Client(HTTP_HOST="localhost")
    first_response = client.get("/cards", {"page": 1, "page_size": 2})
    second_response = client.get("/cards", {"page": 2, "page_size": 2})
    capped_response = client.get("/cards", {"page": 1, "page_size": 200})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert capped_response.status_code == 200
    assert first_response.json()["page_size"] == 2
    assert len(first_response.json()["results"]) == 2
    assert second_response.json()["page"] == 2
    assert second_response.json()["previous_page"] == 1
    assert capped_response.json()["page_size"] == 100
    returned_ids = {row["id"] for row in first_response.json()["results"] + second_response.json()["results"]}
    assert set(created).issubset(returned_ids)


def test_cards_list_pagination_handles_empty_pages() -> None:
    response = Client(HTTP_HOST="localhost").get("/cards", {"page": 999, "page_size": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 999
    assert payload["results"] == []
    assert payload["next_page"] is None


def test_cards_list_filters_preserve_count() -> None:
    keyword = Keyword.objects.first()
    other_keyword = Keyword.objects.exclude(id=keyword.id).first() if keyword is not None else None
    assert keyword is not None and other_keyword is not None

    card_a, version_a = _create_editable_card_version(name="Keyword Match A")
    card_b, version_b = _create_editable_card_version(name="Keyword Match B")
    _card_c, version_c = _create_editable_card_version(name="Keyword Miss")
    _create_card_image(version_a)
    _create_card_image(version_b)
    _create_card_image(version_c)
    replace_card_version_keywords(card_version_id=version_a.id, keyword_ids=[keyword.id])
    replace_card_version_keywords(card_version_id=version_b.id, keyword_ids=[keyword.id])
    replace_card_version_keywords(card_version_id=version_c.id, keyword_ids=[other_keyword.id])

    response = Client(HTTP_HOST="localhost").get("/cards", {"keyword_ids": [keyword.id], "page_size": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert len(payload["results"]) == 1
    assert payload["next_page"] == 2
    returned_ids = {card_a.id, card_b.id}
    assert payload["results"][0]["id"] in returned_ids


def test_cards_list_query_count_does_not_scale_linearly() -> None:
    keyword = Keyword.objects.first()
    tag = Tag.objects.first()
    type_row = Type.objects.first()
    symbol = Symbol.objects.first()
    assert keyword is not None and tag is not None and type_row is not None and symbol is not None

    for index in range(5):
        _card, version = _create_editable_card_version(name=f"Query Budget {index}")
        _create_card_image(version)
        replace_card_version_keywords(card_version_id=version.id, keyword_ids=[keyword.id])
        replace_card_version_tags(card_version_id=version.id, tag_ids=[tag.id])
        replace_card_version_types(card_version_id=version.id, type_ids=[type_row.id])
        replace_card_version_symbols(card_version_id=version.id, symbol_ids=[symbol.id])

    client = Client(HTTP_HOST="localhost")
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/cards", {"page": 1, "page_size": 5})

    assert response.status_code == 200
    assert len(queries) <= 12


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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_latest_version_patch_updates_manual_fields_and_metadata() -> None:
    username = "staff-card-editor-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    keyword = Keyword.objects.first()
    tag = Tag.objects.first()
    type_row = Type.objects.first()
    symbol = Symbol.objects.first()
    assert keyword is not None and tag is not None and type_row is not None and symbol is not None

    card, version = _create_editable_card_version(name="Editable Card")
    replace_card_version_keywords(card_version_id=version.id, keyword_ids=[keyword.id])
    replace_card_version_tags(card_version_id=version.id, tag_ids=[tag.id])
    replace_card_version_types(card_version_id=version.id, type_ids=[type_row.id])
    replace_card_version_symbols(card_version_id=version.id, symbol_ids=[symbol.id])

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={
            "name": "Manual Card Name",
            "rules_text_enriched": "[[symbol:manual-symbol]]: Manual rules text",
            "tag_ids": [],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Manual Card Name"
    assert payload["rules_text_enriched"] == "[[symbol:manual-symbol]]: Manual rules text"
    assert payload["rules_text"] == "manual-symbol: Manual rules text"
    assert payload["tag_ids"] == []
    assert payload["field_sources"]["fields"]["name"] == "manual"
    assert payload["field_sources"]["fields"]["rules_text"] == "manual"
    assert payload["field_sources"]["metadata"]["tags"] == "manual"

    latest = get_latest_card_version(card.id)
    assert latest is not None
    assert latest.name == "Manual Card Name"
    assert latest.rules_text_enriched == "[[symbol:manual-symbol]]: Manual rules text"
    assert latest.rules_text == "manual-symbol: Manual rules text"
    assert [row.id for row in get_tags_for_card_version(latest.id)] == []


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_latest_version_patch_can_restore_and_unlock() -> None:
    username = "staff-card-restore-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    keyword = Keyword.objects.first()
    tag = Tag.objects.first()
    type_row = Type.objects.first()
    symbol = Symbol.objects.first()
    assert keyword is not None and tag is not None and type_row is not None and symbol is not None

    card, version = _create_editable_card_version(name="Restorable Card")
    replace_card_version_keywords(card_version_id=version.id, keyword_ids=[keyword.id])
    replace_card_version_tags(card_version_id=version.id, tag_ids=[])
    replace_card_version_types(card_version_id=version.id, type_ids=[type_row.id])
    replace_card_version_symbols(card_version_id=version.id, symbol_ids=[symbol.id])
    version.rules_text = "Manual override"
    version.type_line = "Manual Type"
    version.field_sources_json = json.dumps(
        {
            "fields": {
                "name": "auto",
                "type_line": "manual",
                "mana_cost": "auto",
                "attack": "auto",
                "health": "auto",
                "rules_text": "manual",
            },
            "metadata": {
                "keywords": "auto",
                "tags": "manual",
                "types": "auto",
                "symbols": "auto",
            },
        }
    )
    version.parsed_snapshot_json = json.dumps(
        {
            "fields": {
                "name": "Restorable Card",
                "type_line": "Parsed Type",
                "mana_cost": "3",
                "attack": None,
                "health": None,
                "rules_text": "Parsed rules",
            },
            "metadata": {
                "keyword_ids": [keyword.id],
                "tag_ids": [tag.id],
                "type_ids": [type_row.id],
                "symbol_ids": [symbol.id],
            },
        }
    )
    version.save(update_fields=["rules_text", "type_line", "field_sources_json", "parsed_snapshot_json"])

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={
            "restore_fields": ["rules_text"],
            "restore_metadata_groups": ["tags"],
            "unlock_fields": ["type_line"],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rules_text"] == "Parsed rules"
    assert payload["tag_ids"] == [tag.id]
    assert payload["field_sources"]["fields"]["rules_text"] == "auto"
    assert payload["field_sources"]["fields"]["type_line"] == "auto"
    assert payload["field_sources"]["metadata"]["tags"] == "auto"

    latest = get_latest_card_version(card.id)
    assert latest is not None
    assert latest.type_line == "Manual Type"
    assert latest.rules_text == "Parsed rules"
    assert [row.id for row in get_tags_for_card_version(latest.id)] == [tag.id]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_symbol_text_token_update_refreshes_rendered_rule_text_for_linked_cards() -> None:
    username = "staff-symbol-refresh-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    symbol = Symbol.objects.create(
        key="exhaust-refresh-test",
        label="Exhaust Refresh Test",
        symbol_type="generic",
        text_token="{EXHAUST}",
    )
    card, version = _create_editable_card_version(name="Symbol Refresh Card")
    version.rules_text_enriched = "[[symbol:exhaust-refresh-test]]: Deal 2 damage."
    version.rules_text = "{EXHAUST}: Deal 2 damage."
    version.save(update_fields=["rules_text_enriched", "rules_text"])
    replace_card_version_symbols(card_version_id=version.id, symbol_ids=[symbol.id])

    response = client.patch(
        f"/settings/symbols/{symbol.id}",
        data={"text_token": "{TAP}"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200

    latest = get_latest_card_version(card.id)
    assert latest is not None
    assert latest.rules_text_enriched == "[[symbol:exhaust-refresh-test]]: Deal 2 damage."
    assert latest.rules_text == "{TAP}: Deal 2 damage."


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_latest_card_reparse_queues_import_job() -> None:
    username = "staff-card-reparse-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    card, version = _create_editable_card_version(name="Reparse Target")
    _create_card_image(version)

    response = client.post(
        f"/cards/{card.id}/reparse",
        data={},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"]
    assert "Queued reparse job" in payload["message"]

    job = ImportJob.objects.get(id=payload["job_id"])
    assert job.template_id == version.template_id
    assert job.options_json == {"reparse_existing": True}
    assert job.total_items == 1

    items = list(ImportJobItem.objects.filter(job_id=job.id))
    assert len(items) == 1
    assert items[0].status == "queued"


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


def _create_editable_card_version(*, name: str) -> tuple[Card, CardVersion]:
    card = Card.objects.create(key=name.lower().replace(" ", "-"), label=name)
    version = CardVersion.objects.create(
        card_id=card.id,
        version_number=1,
        template_id="mtg-like-v1",
        image_hash=f"hash-{name}",
        name=name,
        type_line="Base Type",
        mana_cost="2",
        mana_symbols_json="[]",
        rules_text_raw="Base rules",
        rules_text_enriched="Base rules",
        rules_text="Base rules",
        confidence=0.9,
        field_sources_json=json.dumps(
            {
                "fields": {
                    "name": "auto",
                    "type_line": "auto",
                    "mana_cost": "auto",
                    "attack": "auto",
                    "health": "auto",
                    "rules_text": "auto",
                },
                "metadata": {
                    "keywords": "auto",
                    "tags": "auto",
                    "types": "auto",
                    "symbols": "auto",
                },
            }
        ),
        parsed_snapshot_json=json.dumps(
            {
                "fields": {
                    "name": name,
                    "type_line": "Base Type",
                    "mana_cost": "2",
                    "attack": None,
                    "health": None,
                    "rules_text": "Base rules",
                },
                "metadata": {
                    "keyword_ids": [],
                    "tag_ids": [],
                    "type_ids": [],
                    "symbol_ids": [],
                },
            }
        ),
        is_latest=True,
    )
    ParseResult.objects.create(
        card_version=version,
        raw_ocr_json="{}",
        normalized_fields_json="{}",
        confidence_json="{}",
    )
    card.latest_version_id = version.id
    card.save(update_fields=["latest_version"])
    return card, version


def _create_card_image(version: CardVersion) -> CardVersionImage:
    image_path = settings.image_store_dir / f"checksum-{version.id}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"gallery-image")
    return CardVersionImage.objects.create(
        card_version_id=version.id,
        source_file=build_storage_relative_path("images", image_path.name),
        stored_path=build_storage_relative_path("images", image_path.name),
        checksum=f"checksum-{version.id}",
    )

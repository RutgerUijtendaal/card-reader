import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from card_reader_core.models import Card, CardAlias, CardGroup, CardGroupMember, CardMergeRedirect, CardVersion, CardVersionImage, CardVersionMetadataSuggestion, ContentVersion, Deck, DeckEntry, ImportJob, ImportJobItem, Keyword, MetadataSuggestion, ParseResult, Symbol, Tag, Template, Type  # noqa: E402
from card_reader_core.repositories.cards import DEFAULT_CARD_PAGE_SIZE  # noqa: E402
from card_reader_core.repositories.cards import get_latest_card_version, save_parsed_card  # noqa: E402
from card_reader_core.repositories.import_jobs import create_import_job_with_files  # noqa: E402
from card_reader_core.repositories.metadata import (  # noqa: E402
    get_tags_for_card_version,
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
)
from card_reader_core.services.imports import ImportService  # noqa: E402
from card_reader_core.services.parser_jobs import ImportProcessorService  # noqa: E402
from card_reader_core.config.settings import settings  # noqa: E402
from card_reader_core.storage import build_storage_relative_path, relativize_image_storage_path, resolve_storage_path  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.test import Client, override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from card_reader_api.seeds.users import seed_users  # noqa: E402


def _valid_template_definition(*, region_id: str = "top_bar") -> dict[str, object]:
    return {
        "id": "mtg-like-v1",
        "version": 7,
        "regions": [
            {
                "region_id": region_id,
                "parser_type": "name_mana_cost",
                "cut_region": {
                    "unit": "relative",
                    "x": 0.04,
                    "y": 0.02,
                    "w": 0.92,
                    "h": 0.07,
                },
                "ocr_config": {},
            }
        ],
    }


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
            "content_version_base": "14.1",
            "content_version_description": "Test import version.",
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
        data={
            "template_id": "mtg-like-v1",
            "content_version_base": "14.1",
            "content_version_description": "Test import version.",
            "options_json": "{}",
        },
    )
    assert response.status_code == 400


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_create_import_upload_stores_relative_paths() -> None:
    response = Client(HTTP_HOST="localhost").post(
        "/imports/upload",
        data={
            "template_id": "mtg-like-v1",
            "content_version_base": "14.1",
            "content_version_description": "Test import version.",
            "options_json": "{}",
            "files": SimpleUploadedFile("card.png", b"fake-image-content", content_type="image/png"),
        },
    )

    assert response.status_code == 201
    job = ImportJob.objects.get(id=response.json()["id"])
    item = ImportJobItem.objects.get(job_id=job.id)
    assert job.source_path.startswith("uploads/")
    assert job.content_version is not None
    assert job.content_version.version_number == "14.1.0"
    assert response.json()["content_version"]["version_number"] == "14.1.0"
    assert item.source_file.startswith(f"{job.source_path}/")


@override_settings(CARD_READER_AUTH_ENABLED=False)
@pytest.mark.parametrize("base_version", ["", "14", "14.1.2", "v14.1", "14.a"])
def test_create_import_upload_rejects_invalid_content_version_base(base_version: str) -> None:
    existing_count = ContentVersion.objects.count()
    response = Client(HTTP_HOST="localhost").post(
        "/imports/upload",
        data={
            "template_id": "mtg-like-v1",
            "content_version_base": base_version,
            "content_version_description": "Test import version.",
            "options_json": "{}",
            "files": SimpleUploadedFile("card.png", b"fake-image-content", content_type="image/png"),
        },
    )

    assert response.status_code == 400
    assert ContentVersion.objects.count() == existing_count


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_create_import_upload_rejects_blank_content_version_description() -> None:
    existing_count = ContentVersion.objects.count()
    response = Client(HTTP_HOST="localhost").post(
        "/imports/upload",
        data={
            "template_id": "mtg-like-v1",
            "content_version_base": "14.1",
            "content_version_description": "   ",
            "options_json": "{}",
            "files": SimpleUploadedFile("card.png", b"fake-image-content", content_type="image/png"),
        },
    )

    assert response.status_code == 400
    assert ContentVersion.objects.count() == existing_count


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_create_import_upload_increments_content_version_patch() -> None:
    client = Client(HTTP_HOST="localhost")
    for filename in ["first.png", "second.png"]:
        response = client.post(
            "/imports/upload",
            data={
                "template_id": "mtg-like-v1",
                "content_version_base": "98.7",
                "content_version_description": "Test import version.",
                "options_json": "{}",
                "files": SimpleUploadedFile(filename, b"fake-image-content", content_type="image/png"),
            },
        )
        assert response.status_code == 201

    versions = list(
        ContentVersion.objects.filter(base_version="98.7").order_by("patch").values_list("version_number", flat=True)
    )
    assert versions == ["98.7.0", "98.7.1"]


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_current_content_version_uses_numeric_semantic_sorting() -> None:
    ContentVersion.objects.create(
        version_number="99.9.9",
        base_version="99.9",
        major=99,
        minor=9,
        patch=9,
        description="Older version.",
    )
    ContentVersion.objects.create(
        version_number="99.10.0",
        base_version="99.10",
        major=99,
        minor=10,
        patch=0,
        description="Current version.",
    )

    response = Client(HTTP_HOST="localhost").get("/imports/current-version")

    assert response.status_code == 200
    assert response.json()["version_number"] == "99.10.0"


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_cancel_queued_import_job_marks_it_cancelled() -> None:
    job = ImportJob.objects.create(
        source_path="uploads/test-job",
        template=Template.objects.get(key="mtg-like-v1"),
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
                tag_suggestions=[],
                type_suggestions=[],
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

    for path in [
        "/admin/maintenance/queue-latest-reparse",
        "/admin/maintenance/convert-card-images-to-webp",
    ]:
        staff_response = staff_client.post(path, data={}, content_type="application/json")
        superuser_response = superuser_client.post(path, data={}, content_type="application/json")

        assert staff_response.status_code == 403
        assert superuser_response.status_code == 200


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_manage_catalog_entries() -> None:
    username = "staff-catalog-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    list_response = client.get("/admin/catalog")
    create_response = client.post(
        "/admin/keywords",
        data={"label": "Staff Catalog Keyword", "key": "staff-catalog-keyword"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert list_response.status_code == 200
    assert create_response.status_code == 200


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_catalog_response_groups_known_and_suggested_entries() -> None:
    username = "staff-catalog-suggestions-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(client, username, password)

    card, version = _create_editable_card_version(name="Suggested Catalog Card")
    suggestion = MetadataSuggestion.objects.create(
        kind="tag",
        normalized_value="mystic relic accept auto manual",
        display_value="Mystic Relic Accept Auto Manual",
    )
    CardVersionMetadataSuggestion.objects.create(
        card_version=version,
        suggestion=suggestion,
        source_text="Mystic Relic",
        normalized_source_text="Mystic Relic",
        parse_result=version.parse_result,
    )

    response = client.get("/admin/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert "known" in payload
    assert "suggested" in payload
    assert isinstance(payload["known"]["tags"], list)
    suggested_ids = {row["id"] for row in payload["suggested"]["tags"]}
    assert suggestion.id in suggested_ids
    assert card.id


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_catalog_detail_linked_cards_exclude_deprecated_cards() -> None:
    username = "staff-catalog-deprecated-links-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(client, username, password)

    keyword = Keyword.objects.create(
        key="deprecated-only-keyword",
        label="Deprecated Only Keyword",
        identifiers_json=[],
    )
    deprecated_card, deprecated_version = _create_editable_card_version(name="Deprecated Catalog Link Card")
    deprecated_card.lifecycle_status = "deprecated"
    deprecated_card.save(update_fields=["lifecycle_status"])
    replace_card_version_keywords(card_version_id=deprecated_version.id, keyword_ids=[keyword.id])

    list_response = client.get("/admin/catalog")
    detail_response = client.get(f"/admin/keywords/{keyword.id}")

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    list_keyword = next(row for row in list_response.json()["known"]["keywords"] if row["id"] == keyword.id)
    detail_payload = detail_response.json()
    assert list_keyword["linked_card_count"] == 0
    assert detail_payload["linked_card_count"] == 0
    assert detail_payload["linked_cards"] == []


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_create_keyword_identifiers() -> None:
    username = "staff-keyword-alias-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/admin/keywords",
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
        "/admin/tags",
        data={
            "label": "Weapon",
            "key": "weapon-identifiers-test",
            "identifiers": ["arms", "  WEAPON  "],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    type_response = client.post(
        "/admin/types",
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
def test_staff_can_accept_tag_suggestion_to_existing_and_preserve_manual_cards() -> None:
    username = "staff-suggestion-accept-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    target_tag = Tag.objects.first()
    assert target_tag is not None

    auto_card, auto_version = _create_editable_card_version(name="Suggestion Auto Card")
    manual_card, manual_version = _create_editable_card_version(name="Suggestion Manual Card")
    manual_version.field_sources_json = json.dumps(
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
                "tags": "manual",
                "types": "auto",
                "symbols": "auto",
            },
        }
    )
    manual_version.save(update_fields=["field_sources_json"])

    suggestion = MetadataSuggestion.objects.create(
        kind="tag",
        normalized_value="mystic relic accept manual propagation",
        display_value="Mystic Relic Accept Manual Propagation",
    )
    CardVersionMetadataSuggestion.objects.create(
        card_version=auto_version,
        suggestion=suggestion,
        source_text="Mystic Relic Accept Auto Manual",
        normalized_source_text="Mystic Relic Accept Auto Manual",
        parse_result=auto_version.parse_result,
    )
    CardVersionMetadataSuggestion.objects.create(
        card_version=manual_version,
        suggestion=suggestion,
        source_text="Mystic Relic Accept Auto Manual",
        normalized_source_text="Mystic Relic Accept Auto Manual",
        parse_result=manual_version.parse_result,
    )

    response = client.post(
        f"/admin/suggestions/tag/{suggestion.id}/accept",
        data={"target_id": target_tag.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    suggestion.refresh_from_db()
    target_tag.refresh_from_db()
    assert suggestion.status == "accepted"
    assert suggestion.accepted_tag_id == target_tag.id
    assert "mystic relic accept manual propagation" in target_tag.identifiers_json
    assert [row.id for row in get_tags_for_card_version(auto_version.id)] == [target_tag.id]
    assert [row.id for row in get_tags_for_card_version(manual_version.id)] == []
    assert auto_card.id
    assert manual_card.id


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_reject_type_suggestion() -> None:
    username = "staff-suggestion-reject-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    card, version = _create_editable_card_version(name="Suggestion Reject Card")
    suggestion = MetadataSuggestion.objects.create(
        kind="type",
        normalized_value="ancient mystery",
        display_value="Ancient Mystery",
    )
    CardVersionMetadataSuggestion.objects.create(
        card_version=version,
        suggestion=suggestion,
        source_text="Ancient Mystery",
        normalized_source_text="Ancient Mystery",
        parse_result=version.parse_result,
    )

    response = client.post(
        f"/admin/suggestions/type/{suggestion.id}/reject",
        data={},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    suggestion.refresh_from_db()
    assert suggestion.status == "rejected"
    assert card.id


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_manage_templates() -> None:
    username = "staff-template-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    list_response = client.get("/admin/templates")
    create_response = client.post(
        "/admin/templates",
        data={
            "label": "Staff Template",
            "key": "staff-template",
            "definition_json": _valid_template_definition(),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert list_response.status_code == 200
    assert create_response.status_code == 200


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_template_key_cannot_be_updated() -> None:
    username = "staff-template-key-lock-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    template = Template.objects.create(
        key="immutable-template-key",
        label="Immutable Template",
        definition_json=_valid_template_definition(),
    )

    response = client.patch(
        f"/admin/templates/{template.id}",
        data={"key": "renamed-template-key"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Template key cannot be changed"
    template.refresh_from_db()
    assert template.key == "immutable-template-key"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_template_create_rejects_old_keyed_regions_schema() -> None:
    username = "staff-template-invalid-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/admin/templates",
        data={
            "label": "Invalid Template",
            "key": "invalid-template",
            "definition_json": {
                "id": "invalid-template",
                "version": 6,
                "regions": {
                    "top_bar": {
                        "unit": "relative",
                        "x": 0.04,
                        "y": 0.02,
                        "w": 0.92,
                        "h": 0.07,
                    }
                },
            },
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "definition_json.regions must be a non-empty array"


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
    assert payload["page_size"] == DEFAULT_CARD_PAGE_SIZE
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


def test_card_image_asset_endpoint_serves_immutable_image_path() -> None:
    card, version = _create_editable_card_version(name="Immutable Image Card")
    image = _create_card_image(version)

    response = Client(HTTP_HOST="localhost").get(f"/card-images/{image.stored_path}")

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"gallery-image"
    assert card.id


def test_card_payloads_use_immutable_image_urls() -> None:
    card, version = _create_editable_card_version(name="Immutable Payload Card")
    image = _create_card_image(version)
    expected_image_url = f"/card-images/{image.stored_path}"
    client = Client(HTTP_HOST="localhost")

    list_response = client.get("/cards")
    detail_response = client.get(f"/cards/{card.id}")
    generations_response = client.get(f"/cards/{card.id}/generations")

    assert list_response.status_code == 200
    list_entry = next(row for row in list_response.json()["results"] if row["id"] == card.id)
    assert list_entry["image_url"] == expected_image_url

    assert detail_response.status_code == 200
    assert detail_response.json()["image_url"] == expected_image_url

    assert generations_response.status_code == 200
    assert generations_response.json()[0]["image_url"] == expected_image_url


def test_card_payloads_include_content_version() -> None:
    card, version = _create_editable_card_version(name="Versioned Payload Card")
    content_version = ContentVersion.objects.create(
        version_number="72.3.0",
        base_version="72.3",
        major=72,
        minor=3,
        patch=0,
        description="Versioned payload release.",
    )
    version.content_version = content_version
    version.save(update_fields=["content_version"])
    client = Client(HTTP_HOST="localhost")

    detail_response = client.get(f"/cards/{card.id}")
    generations_response = client.get(f"/cards/{card.id}/generations")

    assert detail_response.status_code == 200
    assert detail_response.json()["content_version"]["version_number"] == "72.3.0"
    assert generations_response.status_code == 200
    assert generations_response.json()[0]["content_version"]["version_number"] == "72.3.0"


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_admin_content_versions_list_counts_linked_cards() -> None:
    _older_card, older_version = _create_editable_card_version(name="Older Content Version Card")
    _latest_card, latest_version = _create_editable_card_version(name="Latest Content Version Card")
    older_content_version = ContentVersion.objects.create(
        version_number="173.1.0",
        base_version="173.1",
        major=173,
        minor=1,
        patch=0,
        description="Older content version.",
    )
    latest_content_version = ContentVersion.objects.create(
        version_number="173.2.0",
        base_version="173.2",
        major=173,
        minor=2,
        patch=0,
        description="Latest content version.",
    )
    older_version.content_version = older_content_version
    older_version.save(update_fields=["content_version"])
    latest_version.content_version = latest_content_version
    latest_version.save(update_fields=["content_version"])

    response = Client(HTTP_HOST="localhost").get("/admin/content-versions")

    assert response.status_code == 200
    payload = response.json()
    assert [row["version_number"] for row in payload[:2]] == ["173.2.0", "173.1.0"]
    latest_row = next(row for row in payload if row["id"] == latest_content_version.id)
    assert latest_row["card_count"] == 1


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_admin_content_version_cards_returns_cards_for_selected_version() -> None:
    matching_card, matching_version = _create_editable_card_version(name="Version Gallery Match")
    _other_card, other_version = _create_editable_card_version(name="Version Gallery Other")
    content_version = ContentVersion.objects.create(
        version_number="74.1.0",
        base_version="74.1",
        major=74,
        minor=1,
        patch=0,
        description="Version gallery.",
    )
    other_content_version = ContentVersion.objects.create(
        version_number="74.2.0",
        base_version="74.2",
        major=74,
        minor=2,
        patch=0,
        description="Other gallery.",
    )
    matching_version.content_version = content_version
    matching_version.save(update_fields=["content_version"])
    other_version.content_version = other_content_version
    other_version.save(update_fields=["content_version"])

    response = Client(HTTP_HOST="localhost").get(f"/admin/content-versions/{content_version.id}/cards")

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == [matching_card.id]
    assert payload[0]["content_version"]["version_number"] == "74.1.0"


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_admin_content_version_patch_updates_version_and_description() -> None:
    content_version = ContentVersion.objects.create(
        version_number="175.1.0",
        base_version="175.1",
        major=175,
        minor=1,
        patch=0,
        description="Old description.",
    )

    response = Client(HTTP_HOST="localhost").patch(
        f"/admin/content-versions/{content_version.id}",
        data={"version_number": "175.2.3", "description": "Updated description."},
        content_type="application/json",
    )

    assert response.status_code == 200
    content_version.refresh_from_db()
    assert content_version.version_number == "175.2.3"
    assert content_version.base_version == "175.2"
    assert content_version.major == 175
    assert content_version.minor == 2
    assert content_version.patch == 3
    assert content_version.description == "Updated description."
    assert response.json()["version_number"] == "175.2.3"


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_admin_content_version_patch_rejects_invalid_version_number() -> None:
    content_version = ContentVersion.objects.create(
        version_number="176.1.0",
        base_version="176.1",
        major=176,
        minor=1,
        patch=0,
        description="Valid description.",
    )

    response = Client(HTTP_HOST="localhost").patch(
        f"/admin/content-versions/{content_version.id}",
        data={"version_number": "176.1"},
        content_type="application/json",
    )

    assert response.status_code == 400
    content_version.refresh_from_db()
    assert content_version.version_number == "176.1.0"


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_admin_content_version_patch_rejects_duplicate_version_number() -> None:
    first = ContentVersion.objects.create(
        version_number="177.1.0",
        base_version="177.1",
        major=177,
        minor=1,
        patch=0,
        description="First.",
    )
    second = ContentVersion.objects.create(
        version_number="177.2.0",
        base_version="177.2",
        major=177,
        minor=2,
        patch=0,
        description="Second.",
    )

    response = Client(HTTP_HOST="localhost").patch(
        f"/admin/content-versions/{second.id}",
        data={"version_number": first.version_number},
        content_type="application/json",
    )

    assert response.status_code == 400
    second.refresh_from_db()
    assert second.version_number == "177.2.0"


def test_card_group_payloads_use_immutable_preview_image_urls() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Immutable Group Anchor")
    member_card, member_version = _create_editable_card_version(name="Immutable Group Member")
    anchor_image = _create_card_image(anchor_version)
    member_image = _create_card_image(member_version)
    group = _create_card_group("immutable-group", anchor_card=anchor_card, members=[anchor_card, member_card])

    response = Client(HTTP_HOST="localhost").get(f"/card-groups/{group.id}")

    assert response.status_code == 200
    members = response.json()["members"]
    assert members[0]["card"]["image_url"] == f"/card-images/{anchor_image.stored_path}"
    assert members[1]["card"]["image_url"] == f"/card-images/{member_image.stored_path}"
    group.delete()


def test_card_payloads_fall_back_to_latest_route_when_stored_image_is_missing() -> None:
    card, version = _create_editable_card_version(name="Fallback Stored Path Card")
    image_path = settings.storage_root_dir / "uploads" / f"{version.id}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"fallback-image")
    CardVersionImage.objects.create(
        card_version_id=version.id,
        source_file=build_storage_relative_path("uploads", image_path.name),
        stored_path=build_storage_relative_path("images", f"missing-{version.id}.png"),
        checksum=f"missing-{version.id}",
    )

    response = Client(HTTP_HOST="localhost").get(f"/cards/{card.id}")

    assert response.status_code == 200
    assert response.json()["image_url"] == f"/cards/{card.id}/image"


def test_card_payloads_omit_image_url_when_no_readable_image_file_exists() -> None:
    card, version = _create_editable_card_version(name="Missing Image File Card")
    CardVersionImage.objects.create(
        card_version_id=version.id,
        source_file=build_storage_relative_path("uploads", f"missing-source-{version.id}.png"),
        stored_path=build_storage_relative_path("images", f"missing-stored-{version.id}.png"),
        checksum=f"missing-both-{version.id}",
    )

    response = Client(HTTP_HOST="localhost").get(f"/cards/{card.id}")

    assert response.status_code == 200
    assert response.json()["image_url"] is None


def test_filters_payload_keeps_symbol_asset_urls_public() -> None:
    symbol = Symbol.objects.create(
        key="asset-url-symbol-test",
        label="Asset URL Symbol Test",
        symbol_type="generic",
        detector_type="template",
        detection_config_json={},
        text_enrichment_json={},
        reference_assets_json=["mana/test-symbol.svg"],
        text_token="{ASSET}",
        enabled=True,
    )

    response = Client(HTTP_HOST="localhost").get("/cards/filters")

    assert response.status_code == 200
    returned = next(row for row in response.json()["symbols"] if row["id"] == symbol.id)
    assert returned["asset_url"] == "/symbols/assets/mana/test-symbol.svg"


def test_filters_payload_includes_type_linked_card_counts() -> None:
    counted_type = _create_type(key="filters-counted-type", label="Filters Counted Type")
    _card, version = _create_editable_card_version(name="Filters Counted Card")
    replace_card_version_types(card_version_id=version.id, type_ids=[counted_type.id])

    response = Client(HTTP_HOST="localhost").get("/cards/filters")

    assert response.status_code == 200
    returned = next(row for row in response.json()["types"] if row["id"] == counted_type.id)
    assert returned["linked_card_count"] == 1


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


def test_cards_list_filters_by_card_ids() -> None:
    card_a, version_a = _create_editable_card_version(name="Card Id Match A")
    card_b, version_b = _create_editable_card_version(name="Card Id Match B")
    _card_c, version_c = _create_editable_card_version(name="Card Id Miss")
    _create_card_image(version_a)
    _create_card_image(version_b)
    _create_card_image(version_c)

    response = Client(HTTP_HOST="localhost").get("/cards", {"card_ids": [card_b.id, card_a.id]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert {row["id"] for row in payload["results"]} == {card_a.id, card_b.id}


def test_cards_list_metadata_match_modes() -> None:
    keywords = list(Keyword.objects.order_by("label")[:2])
    tags = list(Tag.objects.order_by("label")[:2])
    types = list(Type.objects.order_by("label")[:2])
    assert len(keywords) == 2
    assert len(tags) == 2
    assert len(types) == 2

    card_any, version_any = _create_editable_card_version(name="Metadata Any")
    card_all, version_all = _create_editable_card_version(name="Metadata All")
    _card_none, version_none = _create_editable_card_version(name="Metadata None")
    _create_card_image(version_any)
    _create_card_image(version_all)
    _create_card_image(version_none)

    replace_card_version_keywords(card_version_id=version_any.id, keyword_ids=[keywords[0].id])
    replace_card_version_keywords(card_version_id=version_all.id, keyword_ids=[keywords[0].id, keywords[1].id])
    replace_card_version_keywords(card_version_id=version_none.id, keyword_ids=[keywords[1].id])

    replace_card_version_tags(card_version_id=version_any.id, tag_ids=[tags[0].id])
    replace_card_version_tags(card_version_id=version_all.id, tag_ids=[tags[0].id, tags[1].id])
    replace_card_version_tags(card_version_id=version_none.id, tag_ids=[tags[1].id])

    replace_card_version_types(card_version_id=version_any.id, type_ids=[types[0].id])
    replace_card_version_types(card_version_id=version_all.id, type_ids=[types[0].id, types[1].id])
    replace_card_version_types(card_version_id=version_none.id, type_ids=[types[1].id])

    client = Client(HTTP_HOST="localhost")
    keyword_all_response = client.get(
        "/cards",
        {
            "keyword_ids": [keywords[0].id, keywords[1].id],
            "keyword_match": "all",
        },
    )
    tag_all_response = client.get(
        "/cards",
        {
            "tag_ids": [tags[0].id, tags[1].id],
            "tag_match": "all",
        },
    )
    type_all_response = client.get(
        "/cards",
        {
            "type_ids": [types[0].id, types[1].id],
            "type_match": "all",
        },
    )

    assert keyword_all_response.status_code == 200
    assert tag_all_response.status_code == 200
    assert type_all_response.status_code == 200

    keyword_all_ids = {row["id"] for row in keyword_all_response.json()["results"]}
    tag_all_ids = {row["id"] for row in tag_all_response.json()["results"]}
    type_all_ids = {row["id"] for row in type_all_response.json()["results"]}

    assert card_any.id not in keyword_all_ids
    assert card_all.id in keyword_all_ids
    assert card_any.id not in tag_all_ids
    assert card_all.id in tag_all_ids
    assert card_any.id not in type_all_ids
    assert card_all.id in type_all_ids


def test_cards_list_symbol_group_match_modes() -> None:
    mana_symbols = list(Symbol.objects.filter(symbol_type="mana").order_by("label")[:2])
    affinity_symbols = list(Symbol.objects.filter(symbol_type="affinity").order_by("label")[:2])
    assert len(mana_symbols) == 2
    assert len(affinity_symbols) == 2

    card_any, version_any = _create_editable_card_version(name="Mana Any")
    card_all, version_all = _create_editable_card_version(name="Mana All")
    _card_none, version_none = _create_editable_card_version(name="Mana None")
    _create_card_image(version_any)
    _create_card_image(version_all)
    _create_card_image(version_none)
    replace_card_version_symbols(card_version_id=version_any.id, symbol_ids=[mana_symbols[0].id, affinity_symbols[0].id])
    replace_card_version_symbols(
        card_version_id=version_all.id,
        symbol_ids=[mana_symbols[0].id, mana_symbols[1].id, affinity_symbols[0].id, affinity_symbols[1].id],
    )
    replace_card_version_symbols(card_version_id=version_none.id, symbol_ids=[affinity_symbols[1].id])

    client = Client(HTTP_HOST="localhost")

    any_response = client.get(
        "/cards",
        {
            "mana_symbol_ids": [mana_symbols[0].id, mana_symbols[1].id],
            "mana_symbol_match": "any",
        },
    )
    all_response = client.get(
        "/cards",
        {
            "mana_symbol_ids": [mana_symbols[0].id, mana_symbols[1].id],
            "mana_symbol_match": "all",
        },
    )
    affinity_all_response = client.get(
        "/cards",
        {
            "affinity_symbol_ids": [affinity_symbols[0].id, affinity_symbols[1].id],
            "affinity_symbol_match": "all",
        },
    )

    assert any_response.status_code == 200
    assert all_response.status_code == 200
    assert affinity_all_response.status_code == 200

    any_ids = {row["id"] for row in any_response.json()["results"]}
    all_ids = {row["id"] for row in all_response.json()["results"]}
    affinity_all_ids = {row["id"] for row in affinity_all_response.json()["results"]}

    assert card_any.id in any_ids
    assert card_all.id in any_ids
    assert card_any.id not in all_ids
    assert card_all.id in all_ids
    assert card_all.id in affinity_all_ids
    assert card_any.id not in affinity_all_ids


def test_cards_list_symbol_group_exclude_modes() -> None:
    mana_symbols = [
        Symbol.objects.create(
            key=f"exclude-mana-{index}",
            label=f"Exclude Mana {index}",
            symbol_type="mana",
            detector_type="template",
            detection_config_json={},
            text_enrichment_json={},
            reference_assets_json=[],
            text_token=f"{{E{index}}}",
            enabled=True,
        )
        for index in range(3)
    ]

    card_red, version_red = _create_editable_card_version(name="Mana Red")
    card_blue_white, version_blue_white = _create_editable_card_version(name="Mana Blue White")
    card_red_green, version_red_green = _create_editable_card_version(name="Mana Red Green")
    _create_card_image(version_red)
    _create_card_image(version_blue_white)
    _create_card_image(version_red_green)

    replace_card_version_symbols(card_version_id=version_red.id, symbol_ids=[mana_symbols[0].id])
    replace_card_version_symbols(card_version_id=version_blue_white.id, symbol_ids=[mana_symbols[1].id, mana_symbols[2].id])
    replace_card_version_symbols(card_version_id=version_red_green.id, symbol_ids=[mana_symbols[0].id, mana_symbols[2].id])

    client = Client(HTTP_HOST="localhost")

    exclude_response = client.get(
        "/cards",
        {
            "mana_symbol_exclude_ids": [mana_symbols[2].id],
        },
    )
    include_and_exclude_response = client.get(
        "/cards",
        {
            "mana_symbol_ids": [mana_symbols[0].id, mana_symbols[1].id],
            "mana_symbol_match": "any",
            "mana_symbol_exclude_ids": [mana_symbols[2].id],
        },
    )

    assert exclude_response.status_code == 200
    assert include_and_exclude_response.status_code == 200

    exclude_ids = {row["id"] for row in exclude_response.json()["results"]}
    include_and_exclude_ids = {row["id"] for row in include_and_exclude_response.json()["results"]}

    assert card_red.id in exclude_ids
    assert card_blue_white.id not in exclude_ids
    assert card_red_green.id not in exclude_ids

    assert card_red.id in include_and_exclude_ids
    assert card_blue_white.id not in include_and_exclude_ids
    assert card_red_green.id not in include_and_exclude_ids


def test_cards_list_mana_cost_range_filters() -> None:
    card_low, version_low = _create_editable_card_version(name="Mana Value Low")
    card_mid, version_mid = _create_editable_card_version(name="Mana Value Mid")
    card_high, version_high = _create_editable_card_version(name="Mana Value High")
    _create_card_image(version_low)
    _create_card_image(version_mid)
    _create_card_image(version_high)

    version_low.mana_cost = "1"
    version_low.mana_symbols_json = []
    version_low.mana_value = 1
    version_low.save(update_fields=["mana_cost", "mana_symbols_json", "mana_value"])

    version_mid.mana_cost = "X+2"
    version_mid.mana_symbols_json = ["mana-fire", "mana-water", "x"]
    version_mid.mana_value = 2
    version_mid.save(update_fields=["mana_cost", "mana_symbols_json", "mana_value"])

    version_high.mana_cost = "5"
    version_high.mana_symbols_json = ["colorless-mana-3", "mana-fire", "mana-water"]
    version_high.mana_value = 5
    version_high.save(update_fields=["mana_cost", "mana_symbols_json", "mana_value"])

    client = Client(HTTP_HOST="localhost")
    min_response = client.get("/cards", {"mana_cost_min": 2})
    max_response = client.get("/cards", {"mana_cost_max": 2})
    range_response = client.get("/cards", {"mana_cost_min": 2, "mana_cost_max": 5})

    assert min_response.status_code == 200
    assert max_response.status_code == 200
    assert range_response.status_code == 200

    min_ids = {row["id"] for row in min_response.json()["results"]}
    max_ids = {row["id"] for row in max_response.json()["results"]}
    range_ids = {row["id"] for row in range_response.json()["results"]}

    assert card_low.id not in min_ids
    assert card_mid.id in min_ids
    assert card_high.id in min_ids
    assert card_low.id in max_ids
    assert card_mid.id in max_ids
    assert card_high.id not in max_ids
    assert card_low.id not in range_ids
    assert card_mid.id in range_ids
    assert card_high.id in range_ids


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


def test_cards_list_can_return_card_groups() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Grouped Anchor")
    member_card, member_version = _create_editable_card_version(name="Grouped Member")
    extra_card, extra_version = _create_editable_card_version(name="Grouped Extra")
    standalone_card, standalone_version = _create_editable_card_version(name="Grouped Standalone")
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    _create_card_image(extra_version)
    _create_card_image(standalone_version)
    _create_card_group("transform-group", anchor_card=anchor_card, members=[anchor_card, member_card, extra_card])

    response = Client(HTTP_HOST="localhost").get("/cards", {"show_groups": "true"})

    assert response.status_code == 200
    payload = response.json()
    group_rows = [row for row in payload["results"] if row["result_type"] == "card_group"]
    card_rows = [row for row in payload["results"] if row["result_type"] == "card"]
    assert len(group_rows) == 1
    assert group_rows[0]["anchor_card_id"] == anchor_card.id
    assert group_rows[0]["member_count"] == 3
    assert [row["card_id"] for row in group_rows[0]["preview_cards"]] == [
        anchor_card.id,
        member_card.id,
        extra_card.id,
    ]
    assert standalone_card.id in {row["id"] for row in card_rows}
    assert anchor_card.id not in {row["id"] for row in card_rows}
    assert member_card.id not in {row["id"] for row in card_rows}
    assert extra_card.id not in {row["id"] for row in card_rows}


def test_grouped_gallery_preview_images_do_not_query_per_member() -> None:
    cards = []
    for index in range(7):
        card, version = _create_editable_card_version(name=f"Grouped Query Member {index}")
        _create_card_image(version)
        cards.append(card)
    _create_card_group("grouped-query-members", anchor_card=cards[0], members=cards)

    client = Client(HTTP_HOST="localhost")
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/cards", {"show_groups": "true", "q": "Grouped Query Member", "page_size": 100})

    assert response.status_code == 200
    group = next(row for row in response.json()["results"] if row["result_type"] == "card_group")
    assert len(group["preview_cards"]) == len(cards)
    assert len(queries) <= 22


def test_grouped_gallery_hides_deprecated_linked_cards_by_default() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Lifecycle Group Anchor")
    deprecated_card, deprecated_version = _create_editable_card_version(name="Lifecycle Group Deprecated")
    _create_card_image(anchor_version)
    _create_card_image(deprecated_version)
    deprecated_card.lifecycle_status = "deprecated"
    deprecated_card.save(update_fields=["lifecycle_status"])
    _create_card_group("lifecycle-group", anchor_card=anchor_card, members=[anchor_card, deprecated_card])

    client = Client(HTTP_HOST="localhost")
    default_response = client.get("/cards", {"show_groups": "true", "q": "Lifecycle Group", "page_size": 100})
    all_response = client.get(
        "/cards",
        {"show_groups": "true", "q": "Lifecycle Group", "lifecycle_status": "all", "page_size": 100},
    )

    assert default_response.status_code == 200
    assert all_response.status_code == 200
    default_group = next(row for row in default_response.json()["results"] if row["result_type"] == "card_group")
    all_group = next(row for row in all_response.json()["results"] if row["result_type"] == "card_group")
    assert default_group["anchor_card_id"] == anchor_card.id
    assert default_group["member_count"] == 1
    assert [row["card_id"] for row in default_group["preview_cards"]] == [anchor_card.id]
    assert all_group["member_count"] == 2
    assert [row["card_id"] for row in all_group["preview_cards"]] == [anchor_card.id, deprecated_card.id]


def test_cards_list_rejects_unknown_sort() -> None:
    response = Client(HTTP_HOST="localhost").get("/cards", {"sort": "unknown"})

    assert response.status_code == 400
    assert "valid choice" in response.json()["detail"].lower()


def test_cards_list_supports_name_and_mana_sorting() -> None:
    low_card, low_version = _create_editable_card_version(name="Sort Probe Low Mana")
    high_card, high_version = _create_editable_card_version(name="Sort Probe High Mana")
    alpha_card, alpha_version = _create_editable_card_version(name="Sort Probe Alpha Name")
    _create_card_image(low_version)
    _create_card_image(high_version)
    _create_card_image(alpha_version)
    low_version.mana_value = 1
    high_version.mana_value = 7
    alpha_version.mana_value = 3
    low_version.updated_at = timezone.now() - timedelta(days=2)
    high_version.updated_at = timezone.now() - timedelta(days=1)
    alpha_version.updated_at = timezone.now()
    low_version.save(update_fields=["mana_value", "updated_at"])
    high_version.save(update_fields=["mana_value", "updated_at"])
    alpha_version.save(update_fields=["mana_value", "updated_at"])

    client = Client(HTTP_HOST="localhost")
    name_response = client.get("/cards", {"sort": "name_asc", "q": "Sort Probe"})
    mana_response = client.get("/cards", {"sort": "mana_desc", "q": "Sort Probe"})

    assert name_response.status_code == 200
    assert mana_response.status_code == 200
    name_ids = [row["id"] for row in name_response.json()["results"][:3]]
    mana_ids = [row["id"] for row in mana_response.json()["results"][:3]]
    assert name_ids == [alpha_card.id, high_card.id, low_card.id]
    assert mana_ids == [high_card.id, alpha_card.id, low_card.id]


def test_cards_list_supports_type_sorting() -> None:
    spell_type = _create_type(key="sort-type-spell", label="Spell")
    creature_type = _create_type(key="sort-type-creature", label="Creature")
    alpha_type = _create_type(key="sort-type-alpha", label="Alpha")
    zeta_type = _create_type(key="sort-type-zeta", label="Zeta")
    mana_type = _create_type(key="mana", label="Mana")

    arcane_card, arcane_version = _create_editable_card_version(name="Sort Type Arcane Multi")
    hybrid_card, hybrid_version = _create_editable_card_version(name="Sort Type Mana Hybrid")
    blade_card, blade_version = _create_editable_card_version(name="Sort Type Blade Solo")
    alpha_card, alpha_version = _create_editable_card_version(name="Sort Type Alpha Solo")
    zeta_card, zeta_version = _create_editable_card_version(name="Sort Type Zeta Solo")
    untyped_card, untyped_version = _create_editable_card_version(name="Sort Type Untyped")
    mana_card, mana_version = _create_editable_card_version(name="Sort Type Mana Solo")
    _filler_spell_card, filler_spell_version = _create_editable_card_version(name="Priority Spell Filler")
    _filler_mana_one_card, filler_mana_one_version = _create_editable_card_version(name="Priority Mana Filler One")
    _filler_mana_two_card, filler_mana_two_version = _create_editable_card_version(name="Priority Mana Filler Two")
    _filler_mana_three_card, filler_mana_three_version = _create_editable_card_version(name="Priority Mana Filler Three")

    for version in (
        arcane_version,
        hybrid_version,
        blade_version,
        alpha_version,
        zeta_version,
        untyped_version,
        mana_version,
        filler_spell_version,
        filler_mana_one_version,
        filler_mana_two_version,
        filler_mana_three_version,
    ):
        _create_card_image(version)

    replace_card_version_types(card_version_id=arcane_version.id, type_ids=[creature_type.id, spell_type.id])
    replace_card_version_types(card_version_id=hybrid_version.id, type_ids=[spell_type.id, mana_type.id])
    replace_card_version_types(card_version_id=blade_version.id, type_ids=[creature_type.id])
    replace_card_version_types(card_version_id=alpha_version.id, type_ids=[alpha_type.id])
    replace_card_version_types(card_version_id=zeta_version.id, type_ids=[zeta_type.id])
    replace_card_version_types(card_version_id=mana_version.id, type_ids=[mana_type.id])
    replace_card_version_types(card_version_id=filler_spell_version.id, type_ids=[spell_type.id])
    replace_card_version_types(card_version_id=filler_mana_one_version.id, type_ids=[mana_type.id])
    replace_card_version_types(card_version_id=filler_mana_two_version.id, type_ids=[mana_type.id])
    replace_card_version_types(card_version_id=filler_mana_three_version.id, type_ids=[mana_type.id])

    response = Client(HTTP_HOST="localhost").get("/cards", {"sort": "types_asc", "q": "Sort Type"})

    assert response.status_code == 200
    result_ids = [row["id"] for row in response.json()["results"][:7]]
    assert result_ids == [
        arcane_card.id,
        hybrid_card.id,
        blade_card.id,
        alpha_card.id,
        zeta_card.id,
        untyped_card.id,
        mana_card.id,
    ]


def test_cards_list_type_sorting_happens_before_pagination() -> None:
    priority_type = _create_type(key="sort-page-priority", label="A Priority")
    secondary_type = _create_type(key="sort-page-secondary", label="B Secondary")
    mana_type = _create_type(key="mana", label="Mana")

    priority_card, priority_version = _create_editable_card_version(name="Sort Page Type Priority")
    secondary_card, secondary_version = _create_editable_card_version(name="Sort Page Type Secondary")
    untyped_card, untyped_version = _create_editable_card_version(name="Sort Page Type Untyped")
    mana_card, mana_version = _create_editable_card_version(name="Sort Page Type Mana")
    filler_card, filler_version = _create_editable_card_version(name="Sort Page Filler Priority")

    for version in (priority_version, secondary_version, untyped_version, mana_version, filler_version):
        _create_card_image(version)

    replace_card_version_types(card_version_id=priority_version.id, type_ids=[priority_type.id])
    replace_card_version_types(card_version_id=secondary_version.id, type_ids=[secondary_type.id])
    replace_card_version_types(card_version_id=mana_version.id, type_ids=[mana_type.id])
    replace_card_version_types(card_version_id=filler_version.id, type_ids=[priority_type.id])

    client = Client(HTTP_HOST="localhost")
    first_response = client.get(
        "/cards",
        {"sort": "types_asc", "q": "Sort Page Type", "page": 1, "page_size": 2},
    )
    second_response = client.get(
        "/cards",
        {"sort": "types_asc", "q": "Sort Page Type", "page": 2, "page_size": 2},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["count"] == 4
    assert [row["id"] for row in first_response.json()["results"]] == [
        priority_card.id,
        secondary_card.id,
    ]
    assert [row["id"] for row in second_response.json()["results"]] == [
        untyped_card.id,
        mana_card.id,
    ]


def test_grouped_gallery_sort_uses_anchor_card_values() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Sort Group Zephyr Group")
    member_card, member_version = _create_editable_card_version(name="Sort Group Zephyr Member")
    standalone_card, standalone_version = _create_editable_card_version(name="Sort Group Amber Solo")
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    _create_card_image(standalone_version)
    anchor_version.mana_value = 6
    standalone_version.mana_value = 2
    anchor_version.updated_at = timezone.now() - timedelta(hours=1)
    standalone_version.updated_at = timezone.now()
    anchor_version.save(update_fields=["mana_value", "updated_at"])
    standalone_version.save(update_fields=["mana_value", "updated_at"])
    _create_card_group("sorted-group", anchor_card=anchor_card, members=[anchor_card, member_card])

    response = Client(HTTP_HOST="localhost").get(
        "/cards",
        {"show_groups": "true", "sort": "name_asc", "q": "Sort Group"},
    )

    assert response.status_code == 200
    results = response.json()["results"][:2]
    assert results[0]["result_type"] == "card"
    assert results[0]["id"] == standalone_card.id
    assert results[1]["result_type"] == "card_group"
    assert results[1]["anchor_card_id"] == anchor_card.id


def test_grouped_gallery_paginates_before_hydrating_payloads() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Paged Group Beta Anchor")
    member_card, member_version = _create_editable_card_version(name="Paged Group Beta Member")
    alpha_card, alpha_version = _create_editable_card_version(name="Paged Group Alpha Solo")
    zeta_card, zeta_version = _create_editable_card_version(name="Paged Group Zeta Solo")
    for version in (anchor_version, member_version, alpha_version, zeta_version):
        _create_card_image(version)
    _create_card_group("paged-group-beta", anchor_card=anchor_card, members=[anchor_card, member_card])

    client = Client(HTTP_HOST="localhost")
    first_response = client.get(
        "/cards",
        {"show_groups": "true", "sort": "name_asc", "q": "Paged Group", "page": 1, "page_size": 1},
    )
    second_response = client.get(
        "/cards",
        {"show_groups": "true", "sort": "name_asc", "q": "Paged Group", "page": 2, "page_size": 1},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["count"] == 3
    assert first_response.json()["next_page"] == 2
    assert first_response.json()["results"][0]["result_type"] == "card"
    assert first_response.json()["results"][0]["id"] == alpha_card.id
    assert second_response.json()["results"][0]["result_type"] == "card_group"
    assert second_response.json()["results"][0]["anchor_card_id"] == anchor_card.id
    assert zeta_card.id


def test_grouped_gallery_type_sort_uses_anchor_card_types() -> None:
    spell_type = _create_type(key="sort-group-spell", label="Spell")
    creature_type = _create_type(key="sort-group-creature", label="Creature")
    mana_type = _create_type(key="mana", label="Mana")

    anchor_card, anchor_version = _create_editable_card_version(name="Sort Type Group Mana Anchor")
    member_card, member_version = _create_editable_card_version(name="Sort Type Group Spell Member")
    standalone_card, standalone_version = _create_editable_card_version(name="Sort Type Group Creature Solo")
    _filler_spell_card, filler_spell_version = _create_editable_card_version(name="Grouped Priority Spell Filler")

    for version in (anchor_version, member_version, standalone_version, filler_spell_version):
        _create_card_image(version)

    replace_card_version_types(card_version_id=anchor_version.id, type_ids=[mana_type.id])
    replace_card_version_types(card_version_id=member_version.id, type_ids=[spell_type.id])
    replace_card_version_types(card_version_id=standalone_version.id, type_ids=[creature_type.id])
    replace_card_version_types(card_version_id=filler_spell_version.id, type_ids=[spell_type.id])
    _create_card_group("sorted-type-group", anchor_card=anchor_card, members=[anchor_card, member_card])

    response = Client(HTTP_HOST="localhost").get(
        "/cards",
        {"show_groups": "true", "sort": "types_asc", "q": "Sort Type Group"},
    )

    assert response.status_code == 200
    results = response.json()["results"][:2]
    assert results[0]["result_type"] == "card"
    assert results[0]["id"] == standalone_card.id
    assert results[1]["result_type"] == "card_group"
    assert results[1]["anchor_card_id"] == anchor_card.id


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_export_cards_csv_honors_selected_sort() -> None:
    _zebra_card, zebra_version = _create_editable_card_version(name="Sort Export Zebra Export")
    _alpha_card, alpha_version = _create_editable_card_version(name="Sort Export Alpha Export")
    _create_card_image(zebra_version)
    _create_card_image(alpha_version)
    zebra_version.updated_at = timezone.now() - timedelta(days=1)
    alpha_version.updated_at = timezone.now()
    zebra_version.save(update_fields=["updated_at"])
    alpha_version.save(update_fields=["updated_at"])

    response = Client(HTTP_HOST="localhost").get("/exports/csv", {"sort": "name_asc", "q": "Sort Export"})

    assert response.status_code == 200
    rows = response.content.decode("utf-8").splitlines()
    assert rows[1].split(",")[1] == "Sort Export Alpha Export"
    assert rows[2].split(",")[1] == "Sort Export Zebra Export"


def test_card_detail_and_group_detail_include_card_group_membership() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Detail Anchor")
    member_card, member_version = _create_editable_card_version(name="Detail Member")
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    group = _create_card_group("detail-group", anchor_card=anchor_card, members=[anchor_card, member_card])

    client = Client(HTTP_HOST="localhost")
    card_response = client.get(f"/cards/{member_card.id}")
    group_response = client.get(f"/card-groups/{group.id}")

    assert card_response.status_code == 200
    assert group_response.status_code == 200
    card_payload = card_response.json()
    group_payload = group_response.json()
    assert card_payload["card_groups"][0]["id"] == group.id
    assert card_payload["card_groups"][0]["is_anchor"] is False
    assert group_payload["id"] == group.id
    assert [member["card"]["id"] for member in group_payload["members"]] == [anchor_card.id, member_card.id]
    assert group_payload["members"][0]["is_anchor"] is True


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_detail_includes_viewer_visible_deck_references() -> None:
    owner = _create_user("card-deck-reference-owner", "password", is_staff=False)
    other_owner = _create_user("card-deck-reference-other", "password", is_staff=False)
    hero_card, _hero_version = _create_editable_card_version(name="Deck Reference Hero")
    card, version = _create_editable_card_version(name="Deck Reference Included")
    _create_card_image(version)
    hero_card.is_hero = True
    hero_card.save(update_fields=["is_hero"])
    owner_deck = Deck.objects.create(
        owner=owner,
        name="Owner Private Deck",
        visibility="private",
        hero_card=hero_card,
    )
    DeckEntry.objects.create(deck=owner_deck, card=card, quantity=2)
    other_deck = Deck.objects.create(
        owner=other_owner,
        name="Other Private Deck",
        visibility="private",
        hero_card=hero_card,
    )
    DeckEntry.objects.create(deck=other_deck, card=card, quantity=3)

    client = Client(HTTP_HOST="localhost")
    client.force_login(owner)
    owner_response = client.get(f"/cards/{card.id}")
    anonymous_response = Client(HTTP_HOST="localhost").get(f"/cards/{card.id}")

    assert owner_response.status_code == 200
    references = owner_response.json()["deck_references"]
    assert [reference["id"] for reference in references] == [owner_deck.id]
    assert references[0]["name"] == "Owner Private Deck"
    assert references[0]["visibility"] == "private"
    assert references[0]["owner"]["id"] == str(owner.id)
    assert references[0]["hero_card"]["id"] == hero_card.id
    assert references[0]["card_reference"]["is_hero"] is False
    assert references[0]["card_reference"]["mainboard_quantity"] == 2
    assert references[0]["card_reference"]["sideboard_quantity"] == 0
    assert anonymous_response.status_code == 200
    assert anonymous_response.json()["deck_references"] == []


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_detail_limits_deck_references_to_three_latest() -> None:
    owner = _create_user("card-deck-reference-limit-owner", "password", is_staff=False)
    hero_card, _hero_version = _create_editable_card_version(name="Deck Reference Limit Hero")
    card, version = _create_editable_card_version(name="Deck Reference Limit Included")
    _create_card_image(version)
    hero_card.is_hero = True
    hero_card.save(update_fields=["is_hero"])
    decks = []
    for index in range(4):
        deck = Deck.objects.create(
            owner=owner,
            name=f"Deck Reference Limit {index}",
            visibility="private",
            hero_card=hero_card,
        )
        DeckEntry.objects.create(deck=deck, card=card, quantity=1)
        Deck.objects.filter(id=deck.id).update(updated_at=timezone.now() + timedelta(minutes=index))
        decks.append(deck)

    client = Client(HTTP_HOST="localhost")
    client.force_login(owner)
    response = client.get(f"/cards/{card.id}")

    assert response.status_code == 200
    references = response.json()["deck_references"]
    assert [reference["id"] for reference in references] == [deck.id for deck in reversed(decks[-3:])]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_group_detail_includes_anchor_viewer_visible_deck_references() -> None:
    owner = _create_user("group-deck-reference-owner", "password", is_staff=False)
    other_owner = _create_user("group-deck-reference-other", "password", is_staff=False)
    anchor_card, anchor_version = _create_editable_card_version(name="Group Deck Reference Anchor")
    member_card, member_version = _create_editable_card_version(name="Group Deck Reference Member")
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    anchor_card.is_hero = True
    anchor_card.save(update_fields=["is_hero"])
    group = _create_card_group("group-deck-reference", anchor_card=anchor_card, members=[anchor_card, member_card])
    owner_deck = Deck.objects.create(
        owner=owner,
        name="Owner Private Group Deck",
        visibility="private",
        hero_card=anchor_card,
    )
    other_deck = Deck.objects.create(
        owner=other_owner,
        name="Other Private Group Deck",
        visibility="private",
        hero_card=anchor_card,
    )
    DeckEntry.objects.create(deck=other_deck, card=member_card, quantity=3)

    client = Client(HTTP_HOST="localhost")
    client.force_login(owner)
    owner_response = client.get(f"/card-groups/{group.id}")
    anonymous_response = Client(HTTP_HOST="localhost").get(f"/card-groups/{group.id}")

    assert owner_response.status_code == 200
    references = owner_response.json()["anchor_deck_references"]
    assert [reference["id"] for reference in references] == [owner_deck.id]
    assert references[0]["name"] == "Owner Private Group Deck"
    assert references[0]["card_reference"]["is_hero"] is True
    assert references[0]["card_reference"]["mainboard_quantity"] == 0
    assert references[0]["card_reference"]["sideboard_quantity"] == 0
    assert anonymous_response.status_code == 200
    assert anonymous_response.json()["anchor_deck_references"] == []


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_group_detail_limits_anchor_deck_references_to_three_latest() -> None:
    owner = _create_user("group-deck-reference-limit-owner", "password", is_staff=False)
    anchor_card, anchor_version = _create_editable_card_version(name="Group Deck Reference Limit Anchor")
    member_card, member_version = _create_editable_card_version(name="Group Deck Reference Limit Member")
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    anchor_card.is_hero = True
    anchor_card.save(update_fields=["is_hero"])
    group = _create_card_group("group-deck-reference-limit", anchor_card=anchor_card, members=[anchor_card, member_card])
    decks = []
    for index in range(4):
        deck = Deck.objects.create(
            owner=owner,
            name=f"Group Deck Reference Limit {index}",
            visibility="private",
            hero_card=anchor_card,
        )
        Deck.objects.filter(id=deck.id).update(updated_at=timezone.now() + timedelta(minutes=index))
        decks.append(deck)

    client = Client(HTTP_HOST="localhost")
    client.force_login(owner)
    response = client.get(f"/card-groups/{group.id}")

    assert response.status_code == 200
    references = response.json()["anchor_deck_references"]
    assert [reference["id"] for reference in references] == [deck.id for deck in reversed(decks[-3:])]


def test_public_card_group_detail_hides_deprecated_linked_cards_by_default() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Detail Lifecycle Anchor")
    deprecated_card, deprecated_version = _create_editable_card_version(name="Detail Lifecycle Deprecated")
    _create_card_image(anchor_version)
    _create_card_image(deprecated_version)
    deprecated_card.lifecycle_status = "deprecated"
    deprecated_card.save(update_fields=["lifecycle_status"])
    group = _create_card_group("detail-lifecycle-group", anchor_card=anchor_card, members=[anchor_card, deprecated_card])

    client = Client(HTTP_HOST="localhost")
    default_response = client.get(f"/card-groups/{group.id}")
    all_response = client.get(f"/card-groups/{group.id}", {"lifecycle_status": "all"})

    assert default_response.status_code == 200
    assert all_response.status_code == 200
    assert default_response.json()["member_count"] == 1
    assert [member["card"]["id"] for member in default_response.json()["members"]] == [anchor_card.id]
    assert all_response.json()["member_count"] == 2
    assert [member["card"]["id"] for member in all_response.json()["members"]] == [
        anchor_card.id,
        deprecated_card.id,
    ]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_group_anchor_cannot_be_deprecated() -> None:
    username = "staff-anchor-lifecycle-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    anchor_card, anchor_version = _create_editable_card_version(name="Lifecycle Anchor Active")
    member_card, member_version = _create_editable_card_version(name="Lifecycle Anchor Member")
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    _create_card_group("lifecycle-anchor-guard", anchor_card=anchor_card, members=[anchor_card, member_card])

    response = client.patch(
        f"/cards/{anchor_card.id}/latest-version",
        data={"lifecycle_status": "deprecated"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Card group anchors cannot be deprecated."
    anchor_card.refresh_from_db()
    assert anchor_card.lifecycle_status == "active"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_group_management_rejects_deprecated_anchor_but_allows_deprecated_member() -> None:
    username = "staff-deprecated-anchor-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    active_anchor, _active_version = _create_editable_card_version(name="Group Active Anchor")
    active_member, _member_version = _create_editable_card_version(name="Group Active Member")
    deprecated_card, _deprecated_version = _create_editable_card_version(name="Group Deprecated Candidate")
    deprecated_card.lifecycle_status = "deprecated"
    deprecated_card.save(update_fields=["lifecycle_status"])

    deprecated_member_response = client.post(
        "/admin/card-groups",
        data={
            "name": "Deprecated Member Allowed",
            "anchor_card_id": active_anchor.id,
            "members": [
                {"card_id": active_anchor.id, "position": 1},
                {"card_id": deprecated_card.id, "position": 2},
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    deprecated_anchor_response = client.post(
        "/admin/card-groups",
        data={
            "name": "Deprecated Anchor Rejected",
            "anchor_card_id": deprecated_card.id,
            "members": [
                {"card_id": deprecated_card.id, "position": 1},
                {"card_id": active_member.id, "position": 2},
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    update_anchor_response = client.patch(
        f"/admin/card-groups/{deprecated_member_response.json()['id']}",
        data={"anchor_card_id": deprecated_card.id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert deprecated_member_response.status_code == 200
    assert deprecated_anchor_response.status_code == 400
    assert update_anchor_response.status_code == 400
    assert deprecated_anchor_response.json()["detail"] == "Card group anchors cannot be deprecated."
    assert update_anchor_response.json()["detail"] == "Card group anchors cannot be deprecated."


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_manage_card_groups() -> None:
    username = "staff-card-groups-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    anchor_card, _anchor_version = _create_editable_card_version(name="Staff Group Anchor")
    member_card, _member_version = _create_editable_card_version(name="Staff Group Member")
    replacement_card, _replacement_version = _create_editable_card_version(name="Staff Group Replacement")

    create_response = client.post(
        "/admin/card-groups",
        data={
            "name": "Staff Managed Group",
            "anchor_card_id": anchor_card.id,
            "members": [
                {"card_id": anchor_card.id, "position": 1},
                {"card_id": member_card.id, "position": 2},
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert create_response.status_code == 200
    group_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/admin/card-groups/{group_id}",
        data={
            "anchor_card_id": replacement_card.id,
            "members": [
                {"card_id": replacement_card.id, "position": 2},
                {"card_id": member_card.id, "position": 1},
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    list_response = client.get("/admin/card-groups")
    delete_response = client.delete(
        f"/admin/card-groups/{group_id}",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert patch_response.status_code == 200
    assert list_response.status_code == 200
    assert delete_response.status_code == 204
    assert patch_response.json()["anchor_card_id"] == replacement_card.id
    assert [member["card_id"] for member in patch_response.json()["members"]] == [replacement_card.id, member_card.id]
    assert all(row["id"] != group_id for row in client.get("/admin/card-groups").json())


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_staff_can_preview_and_apply_card_merge() -> None:
    target_card, target_version = _create_editable_card_version(name="Renamed Card")
    source_card, source_version = _create_editable_card_version(name="Old Card Name")
    owner = _create_user("merge-deck-owner", "password", is_staff=True)
    deck = Deck.objects.create(owner=owner, name="Merge Deck", hero_card=source_card)
    DeckEntry.objects.create(deck=deck, card=target_card, quantity=1)
    DeckEntry.objects.create(deck=deck, card=source_card, quantity=2)
    _create_card_group("merge-group", anchor_card=source_card, members=[source_card, target_card])

    username = "staff-card-merge-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    payload = {"target_card_id": target_card.id, "source_card_ids": [source_card.id]}
    preview_response = client.post(
        "/admin/card-merges/preview",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert preview_response.status_code == 200
    assert preview_response.json()["can_apply"] is True
    assert preview_response.json()["resulting_version_count"] == 2

    apply_response = client.post(
        "/admin/card-merges/apply",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert apply_response.status_code == 200

    assert not Card.objects.filter(id=source_card.id).exists()
    assert CardAlias.objects.filter(card_id=target_card.id, key=source_card.key).exists()
    assert CardMergeRedirect.objects.filter(old_card_id=source_card.id, target_card_id=target_card.id).exists()
    assert list(CardVersion.objects.filter(card_id=target_card.id).order_by("version_number").values_list("id", flat=True)) == [
        source_version.id,
        target_version.id,
    ]
    assert get_latest_card_version(target_card.id).id == target_version.id
    assert DeckEntry.objects.get(deck=deck, card=target_card).quantity == 3
    deck.refresh_from_db()
    assert deck.hero_card_id == target_card.id

    redirected_response = Client(HTTP_HOST="localhost").get(f"/cards/{source_card.id}")
    assert redirected_response.status_code == 200
    assert redirected_response.json()["id"] == target_card.id


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_merge_endpoints_require_staff() -> None:
    target_card, _target_version = _create_editable_card_version(name="Staff Merge Target")
    source_card, _source_version = _create_editable_card_version(name="Staff Merge Source")
    regular_user = _create_user("regular-card-merge-user", "password", is_staff=False)
    client = Client(HTTP_HOST="localhost")
    client.force_login(regular_user)

    response = client.post(
        "/admin/card-merges/preview",
        data={"target_card_id": target_card.id, "source_card_ids": [source_card.id]},
        content_type="application/json",
    )

    assert response.status_code == 403


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_merge_retargets_existing_redirect_chains() -> None:
    first_card, _first_version = _create_editable_card_version(name="Redirect Chain First")
    middle_card, _middle_version = _create_editable_card_version(name="Redirect Chain Middle")
    final_card, _final_version = _create_editable_card_version(name="Redirect Chain Final")
    username = "staff-card-merge-chain-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    first_payload = {"target_card_id": middle_card.id, "source_card_ids": [first_card.id]}
    first_response = client.post(
        "/admin/card-merges/apply",
        data=first_payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert first_response.status_code == 200

    second_payload = {"target_card_id": final_card.id, "source_card_ids": [middle_card.id]}
    second_response = client.post(
        "/admin/card-merges/apply",
        data=second_payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert second_response.status_code == 200

    assert CardMergeRedirect.objects.get(old_card_id=first_card.id).target_card_id == final_card.id
    assert CardMergeRedirect.objects.get(old_card_id=middle_card.id).target_card_id == final_card.id
    redirected_response = Client(HTTP_HOST="localhost").get(f"/cards/{first_card.id}")
    assert redirected_response.status_code == 200
    assert redirected_response.json()["id"] == final_card.id


def test_import_uses_card_alias_for_renamed_card() -> None:
    target_card, target_version = _create_editable_card_version(name="Canonical Import Card")
    CardAlias.objects.create(card=target_card, key="old-import-card", label="Old Import Card")
    source_file = settings.storage_root_dir / "uploads" / "old-import-card.png"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"old-import-card")
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "old-import-card.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "old-import-card.png"),
    )

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="old-import-card-checksum",
        normalized_fields={
            "name": "Old Import Card",
            "type_line": "Base Type",
            "mana_cost": "1",
            "rules_text": "Rules",
            "rules_text_raw": "Rules",
            "rules_text_enriched": "Rules",
        },
        confidence={"overall": 0.8},
        raw_ocr={},
        reparse_existing=False,
    )

    latest_version = get_latest_card_version(target_card.id)
    assert latest_version is not None
    assert version.card == target_card
    assert version.version_number == target_version.version_number + 1
    assert latest_version.id == version.id


def test_import_assigns_content_version_to_created_card_version() -> None:
    content_version = ContentVersion.objects.create(
        version_number="71.1.0",
        base_version="71.1",
        major=71,
        minor=1,
        patch=0,
        description="Created import version.",
    )
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "content-version-card.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        content_version=content_version,
        total_items=1,
    )
    source_file = resolve_storage_path(build_storage_relative_path("uploads", "content-version-card.png"))
    source_file.parent.mkdir(parents=True, exist_ok=True)
    _write_test_png(source_file)
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "content-version-card.png"),
    )

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="content-version-card-checksum",
        normalized_fields={
            "name": "Content Version Card",
            "type_line": "Base Type",
            "mana_cost": "1",
            "rules_text": "Rules",
            "rules_text_raw": "Rules",
            "rules_text_enriched": "Rules",
        },
        confidence={"overall": 0.8},
        raw_ocr={},
        reparse_existing=False,
    )

    assert version.content_version == content_version


def test_targeted_reparse_preserves_existing_card_version_content_version() -> None:
    _card, target_version = _create_editable_card_version(name="Content Version Reparse")
    original_content_version = ContentVersion.objects.create(
        version_number="171.1.0",
        base_version="171.1",
        major=171,
        minor=1,
        patch=0,
        description="Original import version.",
    )
    target_version.content_version = original_content_version
    target_version.save(update_fields=["content_version"])
    content_version = ContentVersion.objects.create(
        version_number="171.2.0",
        base_version="171.2",
        major=171,
        minor=2,
        patch=0,
        description="Updated import version.",
    )
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "content-version-reparse.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        content_version=content_version,
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "content-version-reparse.png"),
        target_card=target_version.card,
        target_card_version=target_version,
    )

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="content-version-reparse-checksum",
        normalized_fields={
            "name": "Content Version Reparse",
            "type_line": "Changed Type",
            "mana_cost": "2",
            "rules_text": "Changed rules",
            "rules_text_raw": "Changed rules",
            "rules_text_enriched": "Changed rules",
        },
        confidence={"overall": 0.8},
        raw_ocr={},
        reparse_existing=False,
    )

    assert version.id == target_version.id
    assert version.content_version == original_content_version


def test_ordinary_import_matching_latest_checksum_creates_new_content_version_snapshot() -> None:
    card, target_version = _create_editable_card_version(name="Content Version Snapshot Old")
    manual_tag = Tag.objects.create(key="manual-snapshot-tag", label="Manual Snapshot Tag")
    ocr_tag = Tag.objects.create(key="ocr-snapshot-tag", label="OCR Snapshot Tag")
    original_content_version = ContentVersion.objects.create(
        version_number="171.3.0",
        base_version="171.3",
        major=171,
        minor=3,
        patch=0,
        description="Original import version.",
    )
    next_content_version = ContentVersion.objects.create(
        version_number="171.3.1",
        base_version="171.3",
        major=171,
        minor=3,
        patch=1,
        description="Next import version.",
    )
    target_version.content_version = original_content_version
    target_version.image_hash = "content-version-snapshot-checksum"
    target_version.name = "Manually Corrected Snapshot"
    target_version.field_sources_json = {
        "fields": {
            "name": "manual",
            "type_line": "auto",
            "mana_cost": "auto",
            "attack": "auto",
            "health": "auto",
            "rules_text": "auto",
        },
        "metadata": {
            "keywords": "auto",
            "tags": "manual",
            "types": "auto",
            "symbols": "auto",
        },
    }
    target_version.save(update_fields=["content_version", "image_hash", "name", "field_sources_json"])
    replace_card_version_tags(card_version_id=target_version.id, tag_ids=[manual_tag.id])
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "content-version-snapshot.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        content_version=next_content_version,
        total_items=1,
    )
    source_file = resolve_storage_path(build_storage_relative_path("uploads", "content-version-snapshot.png"))
    source_file.parent.mkdir(parents=True, exist_ok=True)
    _write_test_png(source_file)
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "content-version-snapshot.png"),
    )

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="content-version-snapshot-checksum",
        normalized_fields={
            "name": "Content Version Snapshot New",
            "type_line": "Changed Type",
            "mana_cost": "2",
            "rules_text": "Changed rules",
            "rules_text_raw": "Changed rules",
            "rules_text_enriched": "Changed rules",
        },
        confidence={"overall": 0.8},
        raw_ocr={},
        tag_ids=[ocr_tag.id],
        reparse_existing=True,
    )

    target_version.refresh_from_db()
    card.refresh_from_db()
    assert version.id != target_version.id
    assert version.card == card
    assert version.version_number == target_version.version_number + 1
    assert version.name == "Manually Corrected Snapshot"
    assert version.content_version == next_content_version
    assert target_version.content_version == original_content_version
    assert card.latest_version == version
    assert card.key == "manually-corrected-snapshot"
    assert card.label == "Manually Corrected Snapshot"
    assert CardAlias.objects.filter(
        card=card,
        key="content-version-snapshot-old",
        label="Content Version Snapshot Old",
    ).exists()
    assert [tag.id for tag in get_tags_for_card_version(version.id)] == [manual_tag.id]


def test_import_matching_deprecated_card_keeps_card_deprecated_and_warns() -> None:
    target_card, target_version = _create_editable_card_version(name="Deprecated Import Card")
    target_card.lifecycle_status = "deprecated"
    target_card.save(update_fields=["lifecycle_status"])
    source_file = settings.storage_root_dir / "uploads" / "deprecated-import-card.png"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"deprecated-import-card")
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "deprecated-import-card.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "deprecated-import-card.png"),
    )

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="deprecated-import-card-checksum",
        normalized_fields={
            "name": "Deprecated Import Card",
            "type_line": "Base Type",
            "mana_cost": "1",
            "rules_text": "Rules",
            "rules_text_raw": "Rules",
            "rules_text_enriched": "Rules",
        },
        confidence={"overall": 0.8},
        raw_ocr={},
        reparse_existing=False,
    )

    target_card.refresh_from_db()
    item.refresh_from_db()
    assert version.card == target_card
    assert version.version_number == target_version.version_number + 1
    assert target_card.lifecycle_status == "deprecated"
    assert item.status == "completed"
    assert item.warning_code == "matched_deprecated_card"
    assert item.warning_message is not None


def test_targeted_reparse_rolls_back_name_conflict() -> None:
    card, version = _create_editable_card_version(name="Rollback Target")
    _conflicting_card, _conflicting_version = _create_editable_card_version(name="Rollback Conflict")
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "rollback-target.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "rollback-target.png"),
        target_card=card,
        target_card_version=version,
    )
    original_parse_result_count = ParseResult.objects.filter(card_version=version).count()

    with pytest.raises(ValueError, match="Card name conflicts"):
        save_parsed_card(
            item=item,
            template_id="mtg-like-v1",
            checksum="rollback-conflict-checksum",
            normalized_fields={
                "name": "Rollback Conflict",
                "type_line": "Changed Type",
                "mana_cost": "9",
                "rules_text": "Changed rules",
                "rules_text_raw": "Changed rules",
                "rules_text_enriched": "Changed rules",
            },
            confidence={"overall": 0.1},
            raw_ocr={"changed": True},
            reparse_existing=False,
        )

    version.refresh_from_db()
    item.refresh_from_db()
    assert version.name == "Rollback Target"
    assert version.type_line == "Base Type"
    assert version.mana_cost == "2"
    assert item.status == "queued"
    assert ParseResult.objects.filter(card_version=version).count() == original_parse_result_count


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
def test_card_version_promote_sets_historical_version_as_latest() -> None:
    username = "staff-card-promote-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    card, historical = _create_editable_card_version(name="Historical Card")
    latest = CardVersion.objects.create(
        card_id=card.id,
        version_number=2,
        template=historical.template,
        image_hash="hash-latest-card",
        name="Current Card",
        type_line="Current Type",
        mana_cost="4",
        mana_symbols_json="[]",
        mana_value=4,
        rules_text_raw="Current rules",
        rules_text_enriched="Current rules",
        rules_text="Current rules",
        confidence=0.8,
        field_sources_json=historical.field_sources_json,
        parsed_snapshot_json=historical.parsed_snapshot_json,
        is_latest=True,
    )
    historical.is_latest = False
    historical.save(update_fields=["is_latest"])
    card.latest_version = latest
    card.label = latest.name
    card.save(update_fields=["latest_version", "label"])

    response = client.post(
        f"/cards/{card.id}/versions/{historical.id}/promote",
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["version_id"] == historical.id
    assert payload["is_latest"] is True
    assert payload["editable"] is True
    historical.refresh_from_db()
    latest.refresh_from_db()
    card.refresh_from_db()
    assert historical.is_latest is True
    assert latest.is_latest is False
    assert card.latest_version_id == historical.id
    assert card.label == "Historical Card"


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
        f"/admin/symbols/{symbol.id}",
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
    assert job.template.key == version.template.key
    assert job.options_json == {"reparse_existing": True}
    assert job.total_items == 1

    items = list(ImportJobItem.objects.filter(job_id=job.id))
    assert len(items) == 1
    assert items[0].status == "queued"
    assert items[0].target_card_id == card.id
    assert items[0].target_card_version_id == version.id


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_latest_card_reparse_accepts_template_switch() -> None:
    username = "staff-card-reparse-template-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    Template.objects.create(
        key="api-template-switch",
        label="API Template Switch",
        definition_json=_valid_template_definition(region_id="alt_top_bar"),
    )
    card, version = _create_editable_card_version(name="Template Switch Target")
    _create_card_image(version)

    response = client.post(
        f"/cards/{card.id}/reparse",
        data={"template_id": "api-template-switch"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 202
    job = ImportJob.objects.get(id=response.json()["job_id"])
    assert job.template.key == "api-template-switch"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_latest_card_reparse_rejects_unknown_template() -> None:
    username = "staff-card-reparse-template-missing-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    card, version = _create_editable_card_version(name="Template Missing Target")
    _create_card_image(version)

    response = client.post(
        f"/cards/{card.id}/reparse",
        data={"template_id": "missing-template"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown template_id 'missing-template'"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_filtered_maintenance_reparse_queues_only_matching_latest_versions() -> None:
    username = "superuser-filtered-reparse-user"
    password = "password"
    _create_user(username, password, is_staff=True, is_superuser=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    alpha_card, alpha_version = _create_editable_card_version(name="Filtered Alpha Target")
    beta_card, beta_version = _create_editable_card_version(name="Filtered Beta Target")
    _create_card_image(alpha_version)
    _create_card_image(beta_version)

    response = client.post(
        "/admin/maintenance/queue-filtered-latest-reparse",
        data={"card_ids": [alpha_card.id]},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Queued 1 reparse job for 1 latest card image matching the selected filters."
    )

    job = ImportJob.objects.order_by("-created_at").first()
    assert job is not None
    items = list(ImportJobItem.objects.filter(job_id=job.id))
    assert len(items) == 1
    assert items[0].target_card_id == alpha_card.id
    assert items[0].target_card_version_id == alpha_version.id
    assert items[0].target_card_id != beta_card.id


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
    from card_reader_core.models import Template

    template = Template.objects.get(key="mtg-like-v1")
    card = Card.objects.create(key=name.lower().replace(" ", "-"), label=name)
    version = CardVersion.objects.create(
        card_id=card.id,
        version_number=1,
        template=template,
        image_hash=f"hash-{name}",
        name=name,
        type_line="Base Type",
        mana_cost="2",
        mana_symbols_json="[]",
        mana_value=2,
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


def _write_test_png(path: Path) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
        b"\x00\x05\xfe\x02\xfeA\x89\x81\x8b\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _create_type(*, key: str, label: str) -> Type:
    row, _created = Type.objects.update_or_create(
        key=key,
        defaults={
            "label": label,
            "identifiers_json": [label.lower()],
        },
    )
    return row


def _create_card_group(name: str, *, anchor_card: Card, members: list[Card]) -> CardGroup:
    group = CardGroup.objects.create(
        key=name,
        name=name.replace("-", " ").title(),
        anchor_card=anchor_card,
    )
    for index, card in enumerate(members, start=1):
        CardGroupMember.objects.create(group=group, card=card, position=index)
    return group

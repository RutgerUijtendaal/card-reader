import hashlib
import json
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from card_reader_core.models import (
    Card,
    CardAlias,
    CardFactionAssignment,
    CardGroup,
    CardGroupMember,
    CardMergeRedirect,
    CardRoleAssignment,
    CardVersion,
    CardVersionImage,
    CardVersionMetadataSuggestion,
    ContentVersion,
    Deck,
    DeckEntry,
    ImportJob,
    ImportJobItem,
    Keyword,
    MetadataSuggestion,
    ParseResult,
    Symbol,
    Tag,
    Template,
    Type,
)  # noqa: E402
from card_reader_core.repositories.cards import DEFAULT_CARD_PAGE_SIZE  # noqa: E402
from card_reader_core.repositories.cards import (  # noqa: E402
    get_latest_card_version,
    save_parsed_card,
    set_card_mana_families,
    update_latest_card_version,
)
from card_reader_core.repositories.import_jobs import create_import_job_with_files  # noqa: E402
from card_reader_core.repositories.metadata import (  # noqa: E402
    delete_symbol,
    get_tags_for_card_version,
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
    update_symbol,
)
from card_reader_core.services.imports import ImportService  # noqa: E402
from card_reader_core.services.classification_rules import ClassificationRuleService  # noqa: E402
from card_reader_core.services.parser_jobs import ImportProcessorService  # noqa: E402
from card_reader_core.config.settings import settings  # noqa: E402
from card_reader_core.storage import (
    build_storage_relative_path,
    relativize_image_storage_path,
    resolve_storage_path,
)  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.test import Client  # noqa: E402
from django.utils import timezone  # noqa: E402

from card_reader_api.imports.creation import StagedImportUpload  # noqa: E402
from card_reader_api.seeds.users import seed_users  # noqa: E402


def _valid_template_definition(
    *,
    region_id: str = "top_bar",
    parser_type: str = "name_mana_cost",
) -> dict[str, object]:
    return {
        "id": "mtg-like-v1",
        "version": 7,
        "regions": [
            {
                "region_id": region_id,
                "parser_type": parser_type,
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


def test_create_import_upload_rejects_unknown_template() -> None:
    creation_key = str(uuid4())
    response = _staff_client("import-unknown-template-user").post(
        "/imports/upload",
        data={
            "creation_key": creation_key,
            "card_pool": "player",
            "template_id": "unknown-template",
            "content_version_base": "14.1",
            "content_version_description": "Test import version.",
            "options_json": "{}",
            "files": SimpleUploadedFile(
                "card.png", b"fake-image-content", content_type="image/png"
            ),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown template_id 'unknown-template'"
    creation_dir = resolve_storage_path(build_storage_relative_path("uploads", creation_key))
    assert not creation_dir.exists() or list(creation_dir.iterdir()) == []


@pytest.mark.parametrize("omitted_field", ["template_id", "card_pool"])
def test_create_import_upload_requires_explicit_card_setup(omitted_field: str) -> None:
    existing_job_count = ImportJob.objects.count()
    payload: dict[str, object] = {
        "creation_key": str(uuid4()),
        "card_pool": "player",
        "template_id": "mtg-like-v1",
        "content_version_base": "14.1",
        "content_version_description": "Required card setup.",
        "options_json": "{}",
        "files": SimpleUploadedFile(
            "card.png", b"fake-image-content", content_type="image/png"
        ),
    }
    payload.pop(omitted_field)

    response = _staff_client(f"import-missing-{omitted_field}-user").post(
        "/imports/upload",
        data=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This field is required."
    assert ImportJob.objects.count() == existing_job_count


def test_create_import_upload_rejects_unsupported_files() -> None:
    response = _staff_client("import-unsupported-files-user").post(
        "/imports/upload",
        data={
            "creation_key": str(uuid4()),
            "card_pool": "player",
            "template_id": "mtg-like-v1",
            "content_version_base": "14.1",
            "content_version_description": "Test import version.",
            "options_json": "{}",
        },
    )
    assert response.status_code == 400


def test_create_import_upload_stores_relative_paths() -> None:
    response = _staff_client("import-relative-paths-user").post(
        "/imports/upload",
        data={
            "creation_key": str(uuid4()),
            "card_pool": "player",
            "template_id": "mtg-like-v1",
            "content_version_base": "14.1",
            "content_version_description": "Test import version.",
            "options_json": "{}",
            "files": SimpleUploadedFile(
                "card.png", b"fake-image-content", content_type="image/png"
            ),
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


def test_interrupted_upload_is_not_published_and_same_key_can_retry() -> None:
    creation_key = str(uuid4())
    fingerprint = "a" * 64
    content = b"complete-image-content"
    checksum = hashlib.sha256(content).hexdigest()

    class InterruptedUpload(SimpleUploadedFile):
        def chunks(self, chunk_size: int | None = None) -> Iterator[bytes]:
            del chunk_size
            yield b"partial-image"
            raise OSError("connection interrupted")

    with pytest.raises(OSError, match="connection interrupted"):
        StagedImportUpload.publish(
            [(InterruptedUpload("card.png", content, content_type="image/png"), checksum)],
            creation_key=creation_key,
            fingerprint=fingerprint,
        )

    upload_dir = resolve_storage_path(
        build_storage_relative_path("uploads", creation_key, fingerprint)
    )
    target_file = upload_dir / "0000-card.png"
    assert not target_file.exists()
    assert not upload_dir.exists()

    staged = StagedImportUpload.publish(
        [(SimpleUploadedFile("card.png", content, content_type="image/png"), checksum)],
        creation_key=creation_key,
        fingerprint=fingerprint,
    )

    assert staged.relative_path == build_storage_relative_path("uploads", creation_key, fingerprint)
    assert target_file.read_bytes() == content


def test_conflicting_import_payloads_use_isolated_fingerprint_directories() -> None:
    creation_key = str(uuid4())
    first_content = b"first-payload"
    second_content = b"second-payload"

    first = StagedImportUpload.publish(
        [
            (
                SimpleUploadedFile("first.png", first_content, content_type="image/png"),
                hashlib.sha256(first_content).hexdigest(),
            )
        ],
        creation_key=creation_key,
        fingerprint="a" * 64,
    )
    second = StagedImportUpload.publish(
        [
            (
                SimpleUploadedFile("second.png", second_content, content_type="image/png"),
                hashlib.sha256(second_content).hexdigest(),
            )
        ],
        creation_key=creation_key,
        fingerprint="b" * 64,
    )

    assert first.relative_path != second.relative_path
    assert [path.name for path in resolve_storage_path(first.relative_path).iterdir()] == [
        "0000-first.png"
    ]
    assert [path.name for path in resolve_storage_path(second.relative_path).iterdir()] == [
        "0000-second.png"
    ]


def test_create_import_upload_replays_same_creation_key_without_duplicate_work() -> None:
    creation_key = str(uuid4())
    client = _staff_client("import-idempotent-replay-user")

    def submit() -> object:
        return client.post(
            "/imports/upload",
            data={
                "creation_key": creation_key,
                "card_pool": "evil",
                "card_role_mode": "override",
                "card_role_override": json.dumps(["boon", "event"]),
                "card_faction_mode": "override",
                "card_faction_override": json.dumps(["dark", "metal"]),
                "template_id": "mtg-like-v1",
                "content_version_base": "97.1",
                "content_version_description": "Idempotent import.",
                "options_json": "{}",
                "files": SimpleUploadedFile(
                    "card.png",
                    b"idempotent-image-content",
                    content_type="image/png",
                ),
            },
        )

    first = submit()
    second = submit()

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["job_id"] == first.json()["job_id"]
    assert second.json()["idempotent_replay"] is True
    assert ImportJob.objects.filter(creation_key=creation_key).count() == 1
    assert ImportJobItem.objects.filter(job_id=first.json()["job_id"]).count() == 1
    assert ContentVersion.objects.filter(base_version="97.1").count() == 1
    job = ImportJob.objects.get(id=first.json()["job_id"])
    assert job.card_pool == "evil"
    assert job.card_role_mode == "override"
    assert job.card_role_override_json == ["boon", "event"]
    assert job.card_faction_mode == "override"
    assert job.card_faction_override_json == ["dark", "metal"]


def test_import_creation_fingerprint_distinguishes_faction_override() -> None:
    creation_key = str(uuid4())
    client = _staff_client("import-faction-fingerprint-user")
    common = {
        "creation_key": creation_key,
        "card_pool": "evil",
        "card_role_mode": "automatic",
        "template_id": "mtg-like-v1",
        "content_version_base": "97.15",
        "content_version_description": "Faction fingerprint.",
        "options_json": "{}",
    }
    first = client.post(
        "/imports/upload",
        data={
            **common,
            "card_faction_mode": "override",
            "card_faction_override": json.dumps(["order"]),
            "files": SimpleUploadedFile("card.png", b"same-image", content_type="image/png"),
        },
    )
    conflict = client.post(
        "/imports/upload",
        data={
            **common,
            "card_faction_mode": "override",
            "card_faction_override": json.dumps(["blood"]),
            "files": SimpleUploadedFile("card.png", b"same-image", content_type="image/png"),
        },
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert ImportJob.objects.filter(creation_key=creation_key).count() == 1


def test_create_import_upload_rejects_conflicting_creation_key_and_supports_lookup() -> None:
    creation_key = str(uuid4())
    client = _staff_client("import-idempotent-conflict-user")
    common = {
        "creation_key": creation_key,
        "card_pool": "player",
        "template_id": "mtg-like-v1",
        "content_version_base": "97.2",
        "content_version_description": "Creation lookup.",
        "options_json": "{}",
    }
    first = client.post(
        "/imports/upload",
        data={
            **common,
            "files": SimpleUploadedFile("card.png", b"first", content_type="image/png"),
        },
    )
    conflict = client.post(
        "/imports/upload",
        data={
            **common,
            "files": SimpleUploadedFile("card.png", b"different", content_type="image/png"),
        },
    )
    lookup = client.get(f"/imports/by-creation-key/{creation_key}")

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert lookup.status_code == 200
    assert lookup.json()["job_id"] == first.json()["job_id"]
    assert ImportJob.objects.filter(creation_key=creation_key).count() == 1


def test_import_upload_snapshots_rules_and_defaults_to_automatic() -> None:
    template = Template.objects.get(key="mtg-like-v1")
    hero_tag = Tag.objects.create(key="hero-snapshot", label="Hero Snapshot")
    rule = ClassificationRuleService().create_rule(
        card_pool="player",
        target_kind="role",
        target_key="hero",
        source_kind="tag",
        source_id=hero_tag.id,
    )

    response = _staff_client("import-template-snapshot-user").post(
        "/imports/upload",
        data={
            "creation_key": str(uuid4()),
            "card_pool": "player",
            "template_id": template.key,
            "content_version_base": "97.3",
            "content_version_description": "Template snapshot.",
            "options_json": "{}",
            "files": SimpleUploadedFile("card.png", b"snapshot", content_type="image/png"),
        },
    )

    assert response.status_code == 201
    job = ImportJob.objects.get(id=response.json()["job_id"])
    assert job.card_role_mode == "automatic"
    assert job.card_role_override_json == []
    assert job.card_faction_mode == "automatic"
    assert job.card_faction_override_json == []
    snapshot = job.classification_rule_snapshot_json
    assert snapshot["card_pool"] == "player"
    assert snapshot["rules"] == [
        {
            "rule_id": rule.id,
            "card_pool": "player",
            "source_kind": "tag",
            "source_id": hero_tag.id,
            "source_key": "hero-snapshot",
            "source_label": "Hero Snapshot",
            "source_identifiers": [],
            "target_kind": "role",
            "target_key": "hero",
        }
    ]
    original_digest = snapshot["digest"]
    ClassificationRuleService().update_rule(rule_id=rule.id, enabled=False)
    job.refresh_from_db()
    assert job.classification_rule_snapshot_json["digest"] == original_digest


@pytest.mark.parametrize("base_version", ["", "14", "14.1.2", "v14.1", "14.a"])
def test_create_import_upload_rejects_invalid_content_version_base(base_version: str) -> None:
    existing_count = ContentVersion.objects.count()
    response = _staff_client("import-invalid-version-user").post(
        "/imports/upload",
        data={
            "creation_key": str(uuid4()),
            "card_pool": "player",
            "template_id": "mtg-like-v1",
            "content_version_base": base_version,
            "content_version_description": "Test import version.",
            "options_json": "{}",
            "files": SimpleUploadedFile(
                "card.png", b"fake-image-content", content_type="image/png"
            ),
        },
    )

    assert response.status_code == 400
    assert ContentVersion.objects.count() == existing_count


def test_create_import_upload_rejects_blank_content_version_description() -> None:
    existing_count = ContentVersion.objects.count()
    response = _staff_client("import-blank-description-user").post(
        "/imports/upload",
        data={
            "creation_key": str(uuid4()),
            "card_pool": "player",
            "template_id": "mtg-like-v1",
            "content_version_base": "14.1",
            "content_version_description": "   ",
            "options_json": "{}",
            "files": SimpleUploadedFile(
                "card.png", b"fake-image-content", content_type="image/png"
            ),
        },
    )

    assert response.status_code == 400
    assert ContentVersion.objects.count() == existing_count


def test_create_import_upload_increments_content_version_patch() -> None:
    client = _staff_client("import-version-increment-user")
    for filename in ["first.png", "second.png"]:
        response = client.post(
            "/imports/upload",
            data={
                "creation_key": str(uuid4()),
                "card_pool": "player",
                "template_id": "mtg-like-v1",
                "content_version_base": "98.7",
                "content_version_description": "Test import version.",
                "options_json": "{}",
                "files": SimpleUploadedFile(
                    filename, b"fake-image-content", content_type="image/png"
                ),
            },
        )
        assert response.status_code == 201

    versions = list(
        ContentVersion.objects.filter(base_version="98.7")
        .order_by("patch")
        .values_list("version_number", flat=True)
    )
    assert versions == ["98.7.0", "98.7.1"]


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

    response = _staff_client("current-content-version-user").get("/imports/current-version")

    assert response.status_code == 200
    assert response.json()["version_number"] == "99.10.0"


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

    response = _staff_client("cancel-import-job-user").post(
        f"/imports/{job.id}/cancel",
        data={},
        content_type="application/json",
    )

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
        classification_rule_snapshot=ClassificationRuleService().build_snapshot(
            card_pool="player",
            include_roles=True,
            include_factions=True,
        ),
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


def test_processor_uses_frozen_classification_detector_inputs() -> None:
    tag = Tag.objects.create(
        key="frozen-parser-source",
        label="Original Hero Source",
        identifiers_json=["original hero term"],
    )
    classification_rules = ClassificationRuleService()
    classification_rules.create_rule(
        card_pool="player",
        target_kind="role",
        target_key="hero",
        source_kind="tag",
        source_id=tag.id,
    )
    symbol = Symbol.objects.create(
        key="frozen-mana-source",
        label="Original Mana Source",
        symbol_type="mana",
        detector_type="template",
        detection_config_json={"threshold": 0.81},
        text_enrichment_json={"aliases": ["original"]},
        reference_assets_json=["symbols/original.webp"],
        text_token="{F}",
        enabled=True,
    )
    symbol_rule = classification_rules.create_rule(
        card_pool="player",
        target_kind="mana_family",
        target_key="arcane",
        source_kind="symbol",
        source_id=symbol.id,
    )
    image = settings.storage_root_dir / "uploads" / "frozen-parser-job" / "0001.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"frozen-parser-image")
    job = create_import_job_with_files(
        source_path=image.parent,
        template_id="mtg-like-v1",
        options={},
        files=[image],
        classification_rule_snapshot=classification_rules.build_snapshot(
            card_pool="player",
            include_roles=True,
            include_factions=True,
            include_mana_families=True,
        ),
    )

    tag.label = "Edited Hero Source"
    tag.identifiers_json = ["edited hero term"]
    tag.save(update_fields=["label", "identifiers_json", "updated_at"])
    symbol.label = "Edited Mana Source"
    symbol.detection_config_json = {"threshold": 0.2}
    symbol.text_enrichment_json = {"aliases": ["edited"]}
    symbol.reference_assets_json = ["symbols/edited.webp"]
    symbol.text_token = "{EDITED}"
    symbol.enabled = False
    symbol.save(
        update_fields=[
            "label",
            "detection_config_json",
            "text_enrichment_json",
            "reference_assets_json",
            "text_token",
            "enabled",
            "updated_at",
        ]
    )
    classification_rules.delete_rule(rule_id=symbol_rule.id)

    class SnapshotInspectingParser:
        def parse(
            self,
            image_path: Path,
            template_id: str,
            **resources: object,
        ) -> SimpleNamespace:
            known_tags = resources["known_tags"]
            assert isinstance(known_tags, list)
            frozen_tag = next(
                row for row in known_tags if isinstance(row, Tag) and row.id == tag.id
            )
            assert frozen_tag.label == "Original Hero Source"
            assert frozen_tag.identifiers_json == ["original hero term"]
            symbols = resources["symbols"]
            assert isinstance(symbols, list)
            frozen_symbol = next(
                row for row in symbols if isinstance(row, Symbol) and row.id == symbol.id
            )
            assert frozen_symbol.label == "Original Mana Source"
            assert frozen_symbol.detection_config_json == {"threshold": 0.81}
            assert frozen_symbol.text_enrichment_json == {"aliases": ["original"]}
            assert frozen_symbol.reference_assets_json == ["symbols/original.webp"]
            assert frozen_symbol.text_token == "{F}"
            assert frozen_symbol.enabled is True
            return SimpleNamespace(
                checksum="frozen-parser-checksum",
                normalized_fields={
                    "name": "Frozen Snapshot Card",
                    "type_line": "Type",
                    "mana_cost": "",
                    "attack": "",
                    "health": "",
                    "rules_text": "",
                },
                confidence={"overall": 0.9},
                raw_ocr={"source": str(image_path), "template_id": template_id},
                keyword_ids=[],
                tag_ids=[tag.id],
                type_ids=[],
                symbol_ids=[symbol.id],
                tag_suggestions=[],
                type_suggestions=[],
            )

    ImportProcessorService(SnapshotInspectingParser()).process_job(job.id)

    card = Card.objects.get(key="frozen-snapshot-card")
    assert CardRoleAssignment.objects.filter(card=card, role="hero").exists()
    assert list(
        card.mana_family_assignments.values_list("mana_family", flat=True)
    ) == ["arcane"]


def test_card_gallery_routes_are_public() -> None:
    client = Client(HTTP_HOST="localhost")

    assert client.get("/cards").status_code == 200
    assert client.get("/cards/filters").status_code == 200


def test_non_gallery_routes_require_authentication() -> None:
    client = Client(HTTP_HOST="localhost")

    response = client.get("/imports")

    assert response.status_code in {401, 403}


def test_non_gallery_routes_require_staff() -> None:
    staff_client = Client(HTTP_HOST="localhost")
    regular_client = Client(HTTP_HOST="localhost")
    staff_user = _create_user("staff-route-user", "password", is_staff=True)
    regular_user = _create_user("regular-route-user", "password", is_staff=False)
    staff_client.force_login(staff_user)
    regular_client.force_login(regular_user)

    assert staff_client.get("/imports").status_code == 200
    assert regular_client.get("/imports").status_code == 403


def test_maintenance_routes_require_superuser() -> None:
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


def test_catalog_response_groups_known_and_suggested_entries() -> None:
    username = "staff-catalog-suggestions-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(client, username, password)

    card, version = _create_editable_card_version(name="Suggested Catalog Card")
    card.card_pool = "evil"
    card.save(update_fields=["card_pool"])
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card=card, role="boon"),
            CardRoleAssignment(card=card, role="event"),
        ]
    )
    keyword = Keyword.objects.create(
        key="classified-catalog-keyword",
        label="Classified Catalog Keyword",
        identifiers_json=[],
    )
    replace_card_version_keywords(card_version_id=version.id, keyword_ids=[keyword.id])
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
    keyword_detail_response = client.get(f"/admin/keywords/{keyword.id}")
    suggestion_detail_response = client.get(f"/admin/suggestions/tag/{suggestion.id}")

    assert response.status_code == 200
    assert keyword_detail_response.status_code == 200
    assert suggestion_detail_response.status_code == 200
    payload = response.json()
    assert "known" in payload
    assert "suggested" in payload
    assert isinstance(payload["known"]["tags"], list)
    suggested_ids = {row["id"] for row in payload["suggested"]["tags"]}
    assert suggestion.id in suggested_ids
    linked_card = keyword_detail_response.json()["linked_cards"][0]
    occurrence = suggestion_detail_response.json()["occurrences"][0]
    assert linked_card["card_pool"] == "evil"
    assert linked_card["card_roles"] == ["boon", "event"]
    assert occurrence["card_pool"] == "evil"
    assert occurrence["card_roles"] == ["boon", "event"]


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
    deprecated_card, deprecated_version = _create_editable_card_version(
        name="Deprecated Catalog Link Card"
    )
    deprecated_card.lifecycle_status = "deprecated"
    deprecated_card.save(update_fields=["lifecycle_status"])
    replace_card_version_keywords(card_version_id=deprecated_version.id, keyword_ids=[keyword.id])

    list_response = client.get("/admin/catalog")
    detail_response = client.get(f"/admin/keywords/{keyword.id}")

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    list_keyword = next(
        row for row in list_response.json()["known"]["keywords"] if row["id"] == keyword.id
    )
    detail_payload = detail_response.json()
    assert list_keyword["linked_card_count"] == 0
    assert detail_payload["linked_card_count"] == 0
    assert detail_payload["linked_cards"] == []


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
    assert "inferred_card_roles" not in create_response.json()
    assert "inferred_card_factions" not in create_response.json()
    created_template = Template.objects.get(key="staff-template")
    assert created_template.label == "Staff Template"


def test_staff_can_create_name_only_template() -> None:
    client = _staff_client("staff-name-only-template-user")

    response = client.post(
        "/admin/templates",
        data={
            "label": "Name Only Template",
            "key": "name-only-template",
            "definition_json": _valid_template_definition(parser_type="name"),
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["definition_json"]["regions"][0]["parser_type"] == "name"
    assert (
        Template.objects.get(key="name-only-template").definition_json["regions"][0]["parser_type"]
        == "name"
    )


def test_staff_can_update_template_to_name_only() -> None:
    client = _staff_client("staff-update-name-only-template-user")
    template = Template.objects.create(
        key="update-name-only-template",
        label="Update Name Only Template",
        definition_json=_valid_template_definition(),
    )

    response = client.patch(
        f"/admin/templates/{template.id}",
        data={"definition_json": _valid_template_definition(parser_type="name")},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["definition_json"]["regions"][0]["parser_type"] == "name"
    template.refresh_from_db()
    assert template.definition_json["regions"][0]["parser_type"] == "name"


@pytest.mark.parametrize(
    ("first_parser_type", "second_parser_type"),
    [
        ("name", "name"),
        ("name_mana_cost", "name_mana_cost"),
        ("name", "name_mana_cost"),
    ],
)
def test_template_create_rejects_multiple_name_producers(
    first_parser_type: str,
    second_parser_type: str,
) -> None:
    client = _staff_client(f"staff-name-conflict-{first_parser_type}-{second_parser_type}")
    definition = _valid_template_definition(parser_type=first_parser_type)
    definition["regions"].append(  # type: ignore[union-attr]
        {
            "region_id": "second_name_bar",
            "parser_type": second_parser_type,
            "cut_region": {
                "unit": "relative",
                "x": 0.04,
                "y": 0.12,
                "w": 0.92,
                "h": 0.07,
            },
            "ocr_config": {},
        }
    )

    response = client.post(
        "/admin/templates",
        data={
            "label": "Conflicting Name Template",
            "key": f"conflicting-{first_parser_type}-{second_parser_type}",
            "definition_json": definition,
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "only one of name or name_mana_cost may be configured" in response.json()["detail"]


def test_template_preview_cards_are_global_across_authorized_pools() -> None:
    client = _staff_client("global-template-preview-user")
    _create_editable_card_version(name="Player Global Preview", card_pool="player")
    _create_editable_card_version(name="Evil Global Preview", card_pool="evil")
    _create_editable_card_version(name="Neutral Global Preview", card_pool="neutral")

    response = client.get(
        "/admin/templates/preview-cards?q=Global%20Preview&template_id=mtg-like-v1"
    )

    assert response.status_code == 200
    assert {(row["name"], row["card_pool"]) for row in response.json()["results"]} == {
        ("Player Global Preview", "player"),
        ("Evil Global Preview", "evil"),
        ("Neutral Global Preview", "neutral"),
    }


def test_template_preview_cards_require_staff_access() -> None:
    user = _create_user("non-staff-template-preview-user", "password", is_staff=False)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)

    assert client.get("/admin/templates/preview-cards").status_code == 403


def test_template_payload_does_not_expose_removed_classification_hints() -> None:
    response = _staff_client("staff-template-role-validation-user").post(
        "/admin/templates",
        data={
            "label": "Parser Only Template",
            "key": "parser-only-template",
            "definition_json": _valid_template_definition(),
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "inferred_card_roles" not in response.json()
    assert "inferred_card_factions" not in response.json()


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
    assert isinstance(login_response.json()["csrf_token"], str)
    assert login_response.json()["is_staff"] is True
    assert login_response.json()["is_superuser"] is False
    assert me_response.json()["username"] == username
    assert isinstance(me_response.json()["csrf_token"], str)


def test_current_user_reports_unauthenticated_when_no_session() -> None:
    response = Client(HTTP_HOST="localhost").get("/auth/me")
    payload = response.json()

    assert response.status_code == 200
    assert payload["authenticated"] is False
    assert isinstance(payload["csrf_token"], str)


def test_current_user_treats_an_inactive_session_as_unauthenticated() -> None:
    user = _create_user("inactive-session-user", "password", is_staff=True)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    assert response.json()["can_access_admin"] is False
    assert response.json()["accessible_card_pools"] == ["player"]


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


@pytest.mark.django_db(transaction=True)
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
    response_body = b"".join(response.streaming_content)
    response.close()
    assert response_body == b"fake-image"
    assert response["Cache-Control"] == "public, no-cache"
    assert response["ETag"] == f'"checksum-{version.id}"'
    assert response["Last-Modified"]

    head_response = Client(HTTP_HOST="localhost").head(f"/cards/{card.id}/image")
    head_body = b"".join(head_response.streaming_content)
    head_response.close()
    assert head_response.status_code == 200
    assert head_body == b""
    assert head_response["Cache-Control"] == response["Cache-Control"]
    assert head_response["ETag"] == response["ETag"]
    assert head_response["Last-Modified"] == response["Last-Modified"]


@pytest.mark.django_db(transaction=True)
def test_card_gallery_stable_image_url_changes_freshness_headers_with_latest_version() -> None:
    card, first_version = _create_editable_card_version(name="Stable Image Card")
    first_image = _create_card_image(first_version)
    client = Client(HTTP_HOST="localhost")
    stable_path = f"/cards/{card.id}/image"

    first_response = client.get(stable_path)
    first_last_modified = first_response["Last-Modified"]
    first_response.close()

    first_version.is_latest = False
    first_version.save(update_fields=["is_latest", "updated_at"])
    second_version = CardVersion.objects.create(
        card=card,
        version_number=2,
        template=first_version.template,
        image_hash="stable-image-second-hash",
        name=first_version.name,
        type_line=first_version.type_line,
        mana_cost=first_version.mana_cost,
        mana_symbols_json=first_version.mana_symbols_json,
        mana_value=first_version.mana_value,
        rules_text_raw=first_version.rules_text_raw,
        rules_text_enriched=first_version.rules_text_enriched,
        rules_text=first_version.rules_text,
        confidence=first_version.confidence,
        field_sources_json=first_version.field_sources_json,
        parsed_snapshot_json=first_version.parsed_snapshot_json,
        is_latest=True,
        previous_version=first_version,
    )
    second_path = settings.image_store_dir / f"stable-{second_version.id}.png"
    second_path.write_bytes(b"new-stable-image")
    second_image = CardVersionImage.objects.create(
        card_version=second_version,
        source_file=build_storage_relative_path("images", second_path.name),
        stored_path=build_storage_relative_path("images", second_path.name),
        checksum=f"checksum-{second_version.id}",
    )
    card.latest_version = second_version
    card.updated_at = card.updated_at + timedelta(seconds=2)
    card.save(update_fields=["latest_version", "updated_at"])

    second_response = client.get(stable_path)

    assert second_response.status_code == 200
    second_body = b"".join(second_response.streaming_content)
    second_response.close()
    assert second_body == b"new-stable-image"
    assert second_response["ETag"] == f'"{second_image.checksum}"'
    assert second_response["ETag"] != f'"{first_image.checksum}"'
    assert second_response["Last-Modified"] != first_last_modified

    redirect_id = f"merged-{card.id}"
    CardMergeRedirect.objects.create(old_card_id=redirect_id, target_card=card)
    redirect_response = client.head(f"/cards/{redirect_id}/image")
    redirect_response.close()
    assert redirect_response.status_code == 200
    assert redirect_response["ETag"] == second_response["ETag"]
    assert redirect_response["Last-Modified"] == second_response["Last-Modified"]


def test_card_image_asset_endpoint_serves_non_checksum_immutable_image_path() -> None:
    card, version = _create_editable_card_version(name="Immutable Image Card")
    image = _create_card_image(version)
    image.checksum = "different-from-stored-filename"
    image.save(update_fields=["checksum"])

    response = Client(HTTP_HOST="localhost").get(f"/card-images/{image.stored_path}")

    assert response.status_code == 200
    response_body = b"".join(response.streaming_content)
    response.close()
    assert response_body == b"gallery-image"
    assert card.id


@pytest.mark.parametrize("restricted_pool", ["evil", "neutral"])
def test_restricted_card_images_are_hidden_from_non_staff_across_all_routes(
    restricted_pool: str,
) -> None:
    card, version = _create_editable_card_version(
        name=f"Restricted {restricted_pool.title()} Image"
    )
    image = _create_card_image(version)
    card.card_pool = restricted_pool
    card.save(update_fields=["card_pool"])
    anonymous = Client(HTTP_HOST="localhost")
    paths = [
        f"/cards/{card.id}/image",
        f"/cards/{card.id}/versions/{version.id}/image",
        f"/card-images/{image.stored_path}",
    ]

    for path in paths:
        assert anonymous.get(path).status_code == 404

    staff = _staff_client(f"restricted-{restricted_pool}-image-staff")
    responses = [staff.get(path) for path in paths]
    try:
        assert [response.status_code for response in responses] == [200, 200, 200]
    finally:
        for response in responses:
            response.close()


@pytest.mark.parametrize("restricted_pool", ["evil", "neutral"])
def test_restricted_card_collections_and_objects_enforce_pool_scope(
    restricted_pool: str,
) -> None:
    card, _version = _create_editable_card_version(
        name=f"Restricted {restricted_pool.title()} Collection Card"
    )
    card.card_pool = restricted_pool
    card.save(update_fields=["card_pool"])
    anonymous = Client(HTTP_HOST="localhost")
    staff = _staff_client(f"restricted-{restricted_pool}-collection-staff")

    assert anonymous.get("/cards", {"card_pool": restricted_pool}).status_code == 403
    assert anonymous.get(f"/cards/{card.id}").status_code == 404
    assert anonymous.get(f"/cards/{card.id}/generations").status_code == 404

    staff_list = staff.get("/cards", {"card_pool": restricted_pool})
    assert staff_list.status_code == 200
    assert [row["id"] for row in staff_list.json()["results"]] == [card.id]
    assert staff.get(f"/cards/{card.id}").status_code == 200
    assert staff.get(f"/cards/{card.id}/generations").status_code == 200


def test_inactive_staff_session_loses_restricted_card_scope() -> None:
    card, _version = _create_editable_card_version(name="Inactive Staff Restricted Card")
    card.card_pool = "evil"
    card.save(update_fields=["card_pool"])
    user = _create_user("inactive-restricted-staff", "password", is_staff=True)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    assert client.get("/cards", {"card_pool": "evil"}).status_code == 403
    assert client.get(f"/cards/{card.id}").status_code == 404


def test_card_version_image_route_rejects_a_version_owned_by_another_card() -> None:
    player_card, _player_version = _create_editable_card_version(name="Visible Player Card")
    evil_card, evil_version = _create_editable_card_version(name="Restricted Evil Version")
    _create_card_image(evil_version)
    evil_card.card_pool = "evil"
    evil_card.save(update_fields=["card_pool"])
    mismatched_path = f"/cards/{player_card.id}/versions/{evil_version.id}/image"

    assert Client(HTTP_HOST="localhost").get(mismatched_path).status_code == 404
    assert _staff_client("mismatched-version-image-staff").get(mismatched_path).status_code == 404


def test_shared_immutable_image_remains_public_when_any_owning_card_is_player() -> None:
    player_card, player_version = _create_editable_card_version(name="Shared Player Image")
    player_image = _create_card_image(player_version)
    evil_card, evil_version = _create_editable_card_version(name="Shared Evil Image")
    evil_card.card_pool = "evil"
    evil_card.save(update_fields=["card_pool"])
    CardVersionImage.objects.create(
        card_version=evil_version,
        source_file=player_image.source_file,
        stored_path=player_image.stored_path,
        checksum=player_image.checksum,
    )

    response = Client(HTTP_HOST="localhost").get(f"/card-images/{player_image.stored_path}")

    assert response.status_code == 200
    assert player_card.id
    response.close()


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

    response = _staff_client("content-version-list-user").get("/admin/content-versions")

    assert response.status_code == 200
    payload = response.json()
    assert [row["version_number"] for row in payload[:2]] == ["173.2.0", "173.1.0"]
    latest_row = next(row for row in payload if row["id"] == latest_content_version.id)
    assert latest_row["card_count"] == 1


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

    response = _staff_client("content-version-cards-user").get(
        f"/admin/content-versions/{content_version.id}/cards"
    )

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == [matching_card.id]
    assert payload[0]["content_version"]["version_number"] == "74.1.0"


def test_admin_content_version_cards_prefetches_card_roles() -> None:
    content_version = ContentVersion.objects.create(
        version_number="74.3.0",
        base_version="74.3",
        major=74,
        minor=3,
        patch=0,
        description="Role query budget.",
    )
    expected_roles: dict[str, list[str]] = {}
    for index, role in enumerate(["hero", "boon", "event", None]):
        card, version = _create_editable_card_version(name=f"Role Query Budget {index}")
        version.content_version = content_version
        version.save(update_fields=["content_version"])
        if role is not None:
            CardRoleAssignment.objects.create(card=card, role=role)
            expected_roles[card.id] = [role]
        else:
            expected_roles[card.id] = []

    client = _staff_client("content-version-card-role-query-user")
    with CaptureQueriesContext(connection) as queries:
        response = client.get(f"/admin/content-versions/{content_version.id}/cards")

    assert response.status_code == 200
    assert {row["id"]: row["card_roles"] for row in response.json()} == expected_roles
    role_queries = [query for query in queries if "card_role_assignment" in query["sql"]]
    assert len(role_queries) == 1


def test_admin_content_version_patch_updates_version_and_description() -> None:
    content_version = ContentVersion.objects.create(
        version_number="175.1.0",
        base_version="175.1",
        major=175,
        minor=1,
        patch=0,
        description="Old description.",
    )

    response = _staff_client("content-version-patch-user").patch(
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


def test_admin_content_version_patch_rejects_invalid_version_number() -> None:
    content_version = ContentVersion.objects.create(
        version_number="176.1.0",
        base_version="176.1",
        major=176,
        minor=1,
        patch=0,
        description="Valid description.",
    )

    response = _staff_client("content-version-invalid-patch-user").patch(
        f"/admin/content-versions/{content_version.id}",
        data={"version_number": "176.1"},
        content_type="application/json",
    )

    assert response.status_code == 400
    content_version.refresh_from_db()
    assert content_version.version_number == "176.1.0"


@pytest.mark.django_db(transaction=True)
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

    response = _staff_client("content-version-duplicate-patch-user").patch(
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
    group = _create_card_group(
        "immutable-group", anchor_card=anchor_card, members=[anchor_card, member_card]
    )

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


def test_filters_payload_uses_the_canonical_card_role_registry() -> None:
    response = Client(HTTP_HOST="localhost").get("/cards/filters")

    assert response.status_code == 200
    assert response.json()["card_roles"] == [
        {"key": "standard", "label": "Normal", "rank": 0, "derived": True},
        {"key": "hero", "label": "Hero", "rank": 1, "derived": False},
        {"key": "boss", "label": "Boss", "rank": 2, "derived": False},
        {"key": "location", "label": "Location", "rank": 3, "derived": False},
        {"key": "boon", "label": "Boon", "rank": 4, "derived": False},
        {"key": "event", "label": "Event", "rank": 5, "derived": False},
        {"key": "shop_item", "label": "Shop Item", "rank": 6, "derived": False},
    ]
    assert response.json()["card_factions"] == [
        {"key": "order", "label": "Order", "rank": 1},
        {"key": "blood", "label": "Blood", "rank": 2},
        {"key": "dark", "label": "Dark", "rank": 3},
        {"key": "metal", "label": "Metal", "rank": 4},
    ]


def test_filters_payload_includes_the_ordered_mana_family_catalog() -> None:
    arcane_mana = _get_or_create_symbol(key="arcane-mana", label="Arcane Mana", symbol_type="mana")
    arcane_affinity = _get_or_create_symbol(
        key="arcane-affinity", label="Arcane Affinity", symbol_type="affinity"
    )

    response = Client(HTTP_HOST="localhost").get("/cards/filters")

    assert response.status_code == 200
    families = response.json()["mana_families"]
    assert [(row["key"], row["label"], row["rank"]) for row in families] == [
        ("arcane", "Arcane", 0),
        ("dark", "Dark", 1),
        ("divine", "Divine", 2),
        ("martial", "Martial", 3),
        ("occult", "Occult", 4),
        ("primal", "Primal", 5),
    ]
    assert families[0]["mana_symbol"]["id"] == arcane_mana.id
    assert families[0]["affinity_symbol"]["id"] == arcane_affinity.id


def test_filters_payload_includes_type_linked_card_counts() -> None:
    counted_type = _create_type(key="filters-counted-type", label="Filters Counted Type")
    _card, version = _create_editable_card_version(name="Filters Counted Card")
    replace_card_version_types(card_version_id=version.id, type_ids=[counted_type.id])

    response = Client(HTTP_HOST="localhost").get("/cards/filters")

    assert response.status_code == 200
    returned = next(row for row in response.json()["types"] if row["id"] == counted_type.id)
    assert returned["linked_card_count"] == 1


def test_filters_payload_scopes_type_counts_to_accessible_card_pools() -> None:
    counted_type = _create_type(key="filters-pool-counted-type", label="Filters Pool Counted Type")
    _player_card, player_version = _create_editable_card_version(name="Filters Player Counted Card")
    evil_card, evil_version = _create_editable_card_version(name="Filters Evil Counted Card")
    evil_card.card_pool = "evil"
    evil_card.save(update_fields=["card_pool"])
    replace_card_version_types(card_version_id=player_version.id, type_ids=[counted_type.id])
    replace_card_version_types(card_version_id=evil_version.id, type_ids=[counted_type.id])

    public_response = Client(HTTP_HOST="localhost").get("/cards/filters")
    staff_response = _staff_client("filters-pool-count-staff").get("/cards/filters")

    assert public_response.status_code == 200
    assert staff_response.status_code == 200
    public_type = next(
        row for row in public_response.json()["types"] if row["id"] == counted_type.id
    )
    staff_type = next(row for row in staff_response.json()["types"] if row["id"] == counted_type.id)
    assert public_type["linked_card_count"] == 1
    assert staff_type["linked_card_count"] == 2


def test_filters_payload_returns_authorized_pool_registry_in_canonical_order() -> None:
    public_response = Client(HTTP_HOST="localhost").get("/cards/filters")
    staff_response = _staff_client("filters-pool-registry-staff").get("/cards/filters")

    assert public_response.json()["card_pools"] == [
        {"key": "player", "label": "Player", "rank": 0},
    ]
    assert staff_response.json()["card_pools"] == [
        {"key": "player", "label": "Player", "rank": 0},
        {"key": "evil", "label": "Evil", "rank": 1},
        {"key": "neutral", "label": "Neutral", "rank": 2},
    ]

    invalid_response = _staff_client("invalid-pool-staff").get(
        "/cards",
        {"card_pool": "unsupported"},
    )
    assert invalid_response.status_code == 400


def test_filters_payload_orders_types_by_linked_card_count_without_pinning_mana() -> None:
    mana_type = _create_type(key="mana", label="Mana")
    common_type = _create_type(key="filters-order-common-type", label="Filters Order Common Type")
    rare_type = _create_type(key="filters-order-rare-type", label="Filters Order Rare Type")

    for index in range(3):
        _card, version = _create_editable_card_version(name=f"Filters Order Mana Card {index}")
        replace_card_version_types(card_version_id=version.id, type_ids=[mana_type.id])

    for index in range(2):
        _card, version = _create_editable_card_version(name=f"Filters Order Common Card {index}")
        replace_card_version_types(card_version_id=version.id, type_ids=[common_type.id])

    _card, version = _create_editable_card_version(name="Filters Order Rare Card")
    replace_card_version_types(card_version_id=version.id, type_ids=[rare_type.id])

    response = Client(HTTP_HOST="localhost").get("/cards/filters")

    assert response.status_code == 200
    target_keys = {mana_type.key, common_type.key, rare_type.key}
    returned_keys = [row["key"] for row in response.json()["types"] if row["key"] in target_keys]
    assert returned_keys == [mana_type.key, common_type.key, rare_type.key]


def test_storage_paths_resolve_relative_to_storage_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)

    resolved = resolve_storage_path("images/example-card.png")
    from_dev_absolute = relativize_image_storage_path(str(tmp_path / "images" / "example-card.png"))
    from_prd_absolute = relativize_image_storage_path(
        "/var/lib/card-reader/images/example-card.png"
    )

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
    returned_ids = {
        row["id"] for row in first_response.json()["results"] + second_response.json()["results"]
    }
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

    response = Client(HTTP_HOST="localhost").get(
        "/cards", {"keyword_ids": [keyword.id], "page_size": 1}
    )

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
    replace_card_version_keywords(
        card_version_id=version_all.id, keyword_ids=[keywords[0].id, keywords[1].id]
    )
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


def test_cards_list_type_exclusions_combine_with_any_and_all_inclusions() -> None:
    types = [
        Type.objects.create(
            key=f"type-filter-exclude-{index}",
            label=f"Type Filter Exclude {index}",
            identifiers_json=[],
        )
        for index in range(3)
    ]
    card_allowed, version_allowed = _create_editable_card_version(name="Type Exclude Allowed")
    card_excluded, version_excluded = _create_editable_card_version(name="Type Exclude Blocked")
    card_mixed, version_mixed = _create_editable_card_version(name="Type Exclude Mixed")
    card_all, version_all = _create_editable_card_version(name="Type Exclude All")
    for version in (version_allowed, version_excluded, version_mixed, version_all):
        _create_card_image(version)

    replace_card_version_types(card_version_id=version_allowed.id, type_ids=[types[0].id])
    replace_card_version_types(card_version_id=version_excluded.id, type_ids=[types[1].id])
    replace_card_version_types(
        card_version_id=version_mixed.id, type_ids=[types[0].id, types[1].id]
    )
    replace_card_version_types(card_version_id=version_all.id, type_ids=[types[0].id, types[2].id])

    client = Client(HTTP_HOST="localhost")
    exclude_response = client.get(
        "/cards",
        {"type_exclude_ids": [types[1].id, types[2].id]},
    )
    include_any_response = client.get(
        "/cards",
        {
            "type_ids": [types[0].id, types[2].id],
            "type_match": "any",
            "type_exclude_ids": [types[1].id],
        },
    )
    include_all_response = client.get(
        "/cards",
        {
            "type_ids": [types[0].id, types[2].id],
            "type_match": "all",
            "type_exclude_ids": [types[1].id],
        },
    )

    assert exclude_response.status_code == 200
    assert include_any_response.status_code == 200
    assert include_all_response.status_code == 200

    exclude_ids = {row["id"] for row in exclude_response.json()["results"]}
    include_any_ids = {row["id"] for row in include_any_response.json()["results"]}
    include_all_ids = {row["id"] for row in include_all_response.json()["results"]}

    assert card_allowed.id in exclude_ids
    assert card_excluded.id not in exclude_ids
    assert card_mixed.id not in exclude_ids
    assert card_all.id not in exclude_ids
    assert card_allowed.id in include_any_ids
    assert card_all.id in include_any_ids
    assert card_mixed.id not in include_any_ids
    assert card_all.id in include_all_ids
    assert card_allowed.id not in include_all_ids


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
    replace_card_version_symbols(
        card_version_id=version_any.id, symbol_ids=[mana_symbols[0].id, affinity_symbols[0].id]
    )
    replace_card_version_symbols(
        card_version_id=version_all.id,
        symbol_ids=[
            mana_symbols[0].id,
            mana_symbols[1].id,
            affinity_symbols[0].id,
            affinity_symbols[1].id,
        ],
    )
    replace_card_version_symbols(
        card_version_id=version_none.id, symbol_ids=[affinity_symbols[1].id]
    )

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
    replace_card_version_symbols(
        card_version_id=version_blue_white.id, symbol_ids=[mana_symbols[1].id, mana_symbols[2].id]
    )
    replace_card_version_symbols(
        card_version_id=version_red_green.id, symbol_ids=[mana_symbols[0].id, mana_symbols[2].id]
    )

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
    _create_card_group(
        "transform-group", anchor_card=anchor_card, members=[anchor_card, member_card, extra_card]
    )

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
        response = client.get(
            "/cards", {"show_groups": "true", "q": "Grouped Query Member", "page_size": 100}
        )

    assert response.status_code == 200
    group = next(row for row in response.json()["results"] if row["result_type"] == "card_group")
    assert len(group["preview_cards"]) == len(cards)
    assert len(queries) <= 22


def test_grouped_gallery_hides_deprecated_linked_cards_by_default() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Lifecycle Group Anchor")
    deprecated_card, deprecated_version = _create_editable_card_version(
        name="Lifecycle Group Deprecated"
    )
    _create_card_image(anchor_version)
    _create_card_image(deprecated_version)
    deprecated_card.lifecycle_status = "deprecated"
    deprecated_card.save(update_fields=["lifecycle_status"])
    _create_card_group(
        "lifecycle-group", anchor_card=anchor_card, members=[anchor_card, deprecated_card]
    )

    client = Client(HTTP_HOST="localhost")
    default_response = client.get(
        "/cards", {"show_groups": "true", "q": "Lifecycle Group", "page_size": 100}
    )
    all_response = client.get(
        "/cards",
        {
            "show_groups": "true",
            "q": "Lifecycle Group",
            "lifecycle_status": "all",
            "page_size": 100,
        },
    )

    assert default_response.status_code == 200
    assert all_response.status_code == 200
    default_group = next(
        row for row in default_response.json()["results"] if row["result_type"] == "card_group"
    )
    all_group = next(
        row for row in all_response.json()["results"] if row["result_type"] == "card_group"
    )
    assert default_group["anchor_card_id"] == anchor_card.id
    assert default_group["member_count"] == 1
    assert [row["card_id"] for row in default_group["preview_cards"]] == [anchor_card.id]
    assert all_group["member_count"] == 2
    assert [row["card_id"] for row in all_group["preview_cards"]] == [
        anchor_card.id,
        deprecated_card.id,
    ]


def test_cards_list_rejects_unknown_sort() -> None:
    response = Client(HTTP_HOST="localhost").get("/cards", {"sort": "unknown"})

    assert response.status_code == 400
    assert "valid choice" in response.json()["detail"].lower()


def test_cards_list_rejects_unknown_mana_family() -> None:
    response = Client(HTTP_HOST="localhost").get("/cards", {"mana_family_keys": ["unknown"]})

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


def test_cards_list_supports_indexed_mana_family_sorting_and_pagination() -> None:
    cards_and_versions = [
        _create_editable_card_version(name="Family Sort Zeta Arcane"),
        _create_editable_card_version(name="Family Sort Alpha Dark"),
        _create_editable_card_version(name="Family Sort Beta Dual"),
        _create_editable_card_version(name="Family Sort Gamma None"),
    ]
    for _card, version in cards_and_versions:
        _create_card_image(version)
    set_card_mana_families(card=cards_and_versions[0][0], mana_families=("arcane",))
    set_card_mana_families(card=cards_and_versions[1][0], mana_families=("dark",))
    set_card_mana_families(
        card=cards_and_versions[2][0], mana_families=("arcane", "dark")
    )

    client = Client(HTTP_HOST="localhost")
    first_response = client.get(
        "/cards",
        {"sort": "mana_type_asc", "q": "Family Sort", "page": 1, "page_size": 2},
    )
    second_response = client.get(
        "/cards",
        {"sort": "mana_type_asc", "q": "Family Sort", "page": 2, "page_size": 2},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert [row["id"] for row in first_response.json()["results"]] == [
        cards_and_versions[0][0].id,
        cards_and_versions[1][0].id,
    ]
    assert [row["id"] for row in second_response.json()["results"]] == [
        cards_and_versions[2][0].id,
        cards_and_versions[3][0].id,
    ]
    assert [row["mana_family_sort_key"] for row in first_response.json()["results"]] == [0, 1]
    from card_reader_core.repositories.cards.queries import _apply_sql_card_sort

    paginated_query = _apply_sql_card_sort(
        CardVersion.objects.filter(name__icontains="Family Sort"),
        "mana_type_asc",
    ).values_list("id", flat=True)[:2]
    sql = str(paginated_query.query)
    assert "mana_family_sort_key" in sql
    assert "ORDER BY" in sql
    assert "LIMIT 2" in sql


def test_cards_list_filters_stored_mana_family_assignments() -> None:
    rows = [
        _create_editable_card_version(name="Family Filter Mana"),
        _create_editable_card_version(name="Family Filter Affinity"),
        _create_editable_card_version(name="Family Filter Dual"),
        _create_editable_card_version(name="Family Filter Dark"),
    ]
    for _card, version in rows:
        _create_card_image(version)
    set_card_mana_families(card=rows[0][0], mana_families=("arcane",))
    set_card_mana_families(card=rows[1][0], mana_families=("arcane",))
    set_card_mana_families(card=rows[2][0], mana_families=("arcane", "dark"))
    set_card_mana_families(card=rows[3][0], mana_families=("dark",))

    client = Client(HTTP_HOST="localhost")
    any_response = client.get("/cards", {"q": "Family Filter", "mana_family_keys": ["arcane"]})
    all_response = client.get(
        "/cards",
        {
            "q": "Family Filter",
            "mana_family_keys": ["arcane", "dark"],
            "mana_family_match": "all",
        },
    )
    exclude_response = client.get(
        "/cards",
        {"q": "Family Filter", "mana_family_exclude_keys": ["arcane"]},
    )

    assert any_response.status_code == 200
    assert all_response.status_code == 200
    assert exclude_response.status_code == 200
    assert {row["id"] for row in any_response.json()["results"]} == {
        rows[0][0].id,
        rows[1][0].id,
        rows[2][0].id,
    }
    assert [row["id"] for row in all_response.json()["results"]] == [rows[2][0].id]
    assert {row["id"] for row in exclude_response.json()["results"]} == {
        rows[3][0].id,
    }


def test_symbol_mutations_do_not_change_stored_mana_families() -> None:
    symbol = _get_or_create_symbol(
        key="family-sync-unmatched", label="Family Sync", symbol_type="affinity"
    )
    card, version = _create_editable_card_version(name="Family Synchronization")
    set_card_mana_families(card=card, mana_families=("arcane",))
    replace_card_version_symbols(card_version_id=version.id, symbol_ids=[symbol.id])
    card.refresh_from_db()
    assert card.mana_family_sort_key == 0

    update_symbol(entry_id=str(symbol.id), updates={"key": "primal-affinity"})
    card.refresh_from_db()
    assert card.mana_family_sort_key == 0

    assert delete_symbol(entry_id=str(symbol.id)) is True
    card.refresh_from_db()
    assert card.mana_family_sort_key == 0

    arcane_symbol = _get_or_create_symbol(
        key="arcane-mana",
        label="Arcane Mana",
        symbol_type="mana",
    )
    updated = update_latest_card_version(
        card_id=card.id,
        updates={"symbol_ids": [arcane_symbol.id]},
        restore_fields=[],
        restore_metadata_groups=[],
        unlock_fields=[],
        unlock_metadata_groups=[],
    )
    assert updated is not None
    updated_card, _updated_version = updated
    updated_card.refresh_from_db()
    assert updated_card.mana_family_sort_key == 0


def test_cards_list_uses_pool_aware_player_default_before_pagination() -> None:
    arcane_hero, arcane_hero_version = _create_editable_card_version(
        name="Default Player Arcane Hero"
    )
    arcane_normal_low, arcane_normal_low_version = _create_editable_card_version(
        name="Default Player Arcane Normal Low"
    )
    arcane_normal_high, arcane_normal_high_version = _create_editable_card_version(
        name="Default Player Arcane Normal High"
    )
    arcane_normal_null, arcane_normal_null_version = _create_editable_card_version(
        name="Default Player Arcane Normal Null"
    )
    arcane_boss, arcane_boss_version = _create_editable_card_version(
        name="Default Player Arcane Boss"
    )
    dark_hero, dark_hero_version = _create_editable_card_version(name="Default Player Dark Hero")

    for version in (
        arcane_hero_version,
        arcane_normal_low_version,
        arcane_normal_high_version,
        arcane_normal_null_version,
        arcane_boss_version,
        dark_hero_version,
    ):
        _create_card_image(version)
    for card, version, mana_value in (
        (arcane_hero, arcane_hero_version, 6),
        (arcane_normal_low, arcane_normal_low_version, 1),
        (arcane_normal_high, arcane_normal_high_version, 4),
        (arcane_boss, arcane_boss_version, 0),
    ):
        set_card_mana_families(card=card, mana_families=("arcane",))
        version.mana_value = mana_value
        version.save(update_fields=["mana_value"])
    set_card_mana_families(card=arcane_normal_null, mana_families=("arcane",))
    arcane_normal_null_version.mana_value = None
    arcane_normal_null_version.save(update_fields=["mana_value"])
    set_card_mana_families(card=dark_hero, mana_families=("dark",))
    dark_hero_version.mana_value = 0
    dark_hero_version.save(update_fields=["mana_value"])
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card=arcane_hero, role="hero"),
            CardRoleAssignment(card=arcane_boss, role="boss"),
            CardRoleAssignment(card=dark_hero, role="hero"),
        ]
    )

    client = Client(HTTP_HOST="localhost")
    first_response = client.get("/cards", {"q": "Default Player", "page": 1, "page_size": 2})
    second_response = client.get("/cards", {"q": "Default Player", "page": 2, "page_size": 2})
    third_response = client.get("/cards", {"q": "Default Player", "page": 3, "page_size": 2})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 200
    assert [row["id"] for row in first_response.json()["results"]] == [
        arcane_hero.id,
        arcane_normal_low.id,
    ]
    assert [row["id"] for row in second_response.json()["results"]] == [
        arcane_normal_high.id,
        arcane_normal_null.id,
    ]
    assert [row["id"] for row in third_response.json()["results"]] == [
        arcane_boss.id,
        dark_hero.id,
    ]


def test_cards_list_uses_evil_faction_default_order() -> None:
    order_boss, order_boss_version = _create_editable_card_version(
        name="Default Evil Order Boss", card_pool="evil"
    )
    order_location, order_location_version = _create_editable_card_version(
        name="Default Evil Order Location", card_pool="evil"
    )
    order_normal_low, order_normal_low_version = _create_editable_card_version(
        name="Default Evil Order Normal Low", card_pool="evil"
    )
    order_normal_high, order_normal_high_version = _create_editable_card_version(
        name="Default Evil Order Normal High", card_pool="evil"
    )
    blood_boss, blood_boss_version = _create_editable_card_version(
        name="Default Evil Blood Boss", card_pool="evil"
    )
    dark_boss, dark_boss_version = _create_editable_card_version(
        name="Default Evil Dark Boss", card_pool="evil"
    )
    metal_boss, metal_boss_version = _create_editable_card_version(
        name="Default Evil Metal Boss", card_pool="evil"
    )
    no_faction_boss, no_faction_boss_version = _create_editable_card_version(
        name="Default Evil No Faction Boss", card_pool="evil"
    )
    for version, mana_value in (
        (order_boss_version, 9),
        (order_location_version, 0),
        (order_normal_low_version, 1),
        (order_normal_high_version, 5),
        (blood_boss_version, 0),
        (dark_boss_version, 0),
        (metal_boss_version, 0),
        (no_faction_boss_version, 0),
    ):
        _create_card_image(version)
        version.mana_value = mana_value
        version.save(update_fields=["mana_value"])
    CardFactionAssignment.objects.bulk_create(
        [
            CardFactionAssignment(card=order_boss, faction="order"),
            CardFactionAssignment(card=order_location, faction="order"),
            CardFactionAssignment(card=order_normal_low, faction="order"),
            CardFactionAssignment(card=order_normal_high, faction="order"),
            CardFactionAssignment(card=blood_boss, faction="blood"),
            CardFactionAssignment(card=dark_boss, faction="dark"),
            CardFactionAssignment(card=metal_boss, faction="metal"),
        ]
    )
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card=order_boss, role="boss"),
            CardRoleAssignment(card=order_location, role="location"),
            CardRoleAssignment(card=blood_boss, role="boss"),
            CardRoleAssignment(card=dark_boss, role="boss"),
            CardRoleAssignment(card=metal_boss, role="boss"),
            CardRoleAssignment(card=no_faction_boss, role="boss"),
        ]
    )

    response = _staff_client("evil-default-sort-user").get(
        "/cards", {"card_pool": "evil", "q": "Default Evil"}
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [
        order_boss.id,
        order_location.id,
        order_normal_low.id,
        order_normal_high.id,
        blood_boss.id,
        dark_boss.id,
        metal_boss.id,
        no_faction_boss.id,
    ]


def test_cards_list_uses_neutral_role_default_order() -> None:
    normal_card, normal_version = _create_editable_card_version(
        name="Default Neutral Normal", card_pool="neutral"
    )
    boon_card, boon_version = _create_editable_card_version(
        name="Default Neutral Boon", card_pool="neutral"
    )
    boon_event_card, boon_event_version = _create_editable_card_version(
        name="Default Neutral Boon Event", card_pool="neutral"
    )
    event_card, event_version = _create_editable_card_version(
        name="Default Neutral Event", card_pool="neutral"
    )
    shop_card, shop_version = _create_editable_card_version(
        name="Default Neutral Shop", card_pool="neutral"
    )
    hero_card, hero_version = _create_editable_card_version(
        name="Default Neutral Hero", card_pool="neutral"
    )
    boss_card, boss_version = _create_editable_card_version(
        name="Default Neutral Boss", card_pool="neutral"
    )
    location_card, location_version = _create_editable_card_version(
        name="Default Neutral Location", card_pool="neutral"
    )
    for version in (
        normal_version,
        boon_version,
        boon_event_version,
        event_version,
        shop_version,
        hero_version,
        boss_version,
        location_version,
    ):
        _create_card_image(version)
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card=boon_card, role="boon"),
            CardRoleAssignment(card=boon_event_card, role="boon"),
            CardRoleAssignment(card=boon_event_card, role="event"),
            CardRoleAssignment(card=event_card, role="event"),
            CardRoleAssignment(card=shop_card, role="shop_item"),
            CardRoleAssignment(card=hero_card, role="hero"),
            CardRoleAssignment(card=boss_card, role="boss"),
            CardRoleAssignment(card=location_card, role="location"),
        ]
    )

    response = _staff_client("neutral-default-sort-user").get(
        "/cards", {"card_pool": "neutral", "q": "Default Neutral"}
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [
        normal_card.id,
        hero_card.id,
        boss_card.id,
        location_card.id,
        boon_card.id,
        boon_event_card.id,
        event_card.id,
        shop_card.id,
    ]


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
    _filler_spell_card, filler_spell_version = _create_editable_card_version(
        name="Priority Spell Filler"
    )
    _filler_mana_one_card, filler_mana_one_version = _create_editable_card_version(
        name="Priority Mana Filler One"
    )
    _filler_mana_two_card, filler_mana_two_version = _create_editable_card_version(
        name="Priority Mana Filler Two"
    )
    _filler_mana_three_card, filler_mana_three_version = _create_editable_card_version(
        name="Priority Mana Filler Three"
    )

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

    replace_card_version_types(
        card_version_id=arcane_version.id, type_ids=[creature_type.id, spell_type.id]
    )
    replace_card_version_types(
        card_version_id=hybrid_version.id, type_ids=[spell_type.id, mana_type.id]
    )
    replace_card_version_types(card_version_id=blade_version.id, type_ids=[creature_type.id])
    replace_card_version_types(card_version_id=alpha_version.id, type_ids=[alpha_type.id])
    replace_card_version_types(card_version_id=zeta_version.id, type_ids=[zeta_type.id])
    replace_card_version_types(card_version_id=mana_version.id, type_ids=[mana_type.id])
    replace_card_version_types(card_version_id=filler_spell_version.id, type_ids=[spell_type.id])
    replace_card_version_types(card_version_id=filler_mana_one_version.id, type_ids=[mana_type.id])
    replace_card_version_types(card_version_id=filler_mana_two_version.id, type_ids=[mana_type.id])
    replace_card_version_types(
        card_version_id=filler_mana_three_version.id, type_ids=[mana_type.id]
    )

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
    secondary_card, secondary_version = _create_editable_card_version(
        name="Sort Page Type Secondary"
    )
    untyped_card, untyped_version = _create_editable_card_version(name="Sort Page Type Untyped")
    mana_card, mana_version = _create_editable_card_version(name="Sort Page Type Mana")
    filler_card, filler_version = _create_editable_card_version(name="Sort Page Filler Priority")

    for version in (
        priority_version,
        secondary_version,
        untyped_version,
        mana_version,
        filler_version,
    ):
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


def test_cards_list_type_sort_uses_type_key_when_counts_and_labels_tie() -> None:
    alpha_type = _create_type(key="sort-type-tie-alpha", label="Sort Type Tie")
    zeta_type = _create_type(key="sort-type-tie-zeta", label="Sort Type Tie")
    alpha_card, alpha_version = _create_editable_card_version(
        name="Sort Type Tie Zulu Card"
    )
    zeta_card, zeta_version = _create_editable_card_version(
        name="Sort Type Tie Alpha Card"
    )
    for version in (alpha_version, zeta_version):
        _create_card_image(version)
    replace_card_version_types(card_version_id=alpha_version.id, type_ids=[alpha_type.id])
    replace_card_version_types(card_version_id=zeta_version.id, type_ids=[zeta_type.id])

    response = Client(HTTP_HOST="localhost").get(
        "/cards",
        {"sort": "types_asc", "q": "Sort Type Tie"},
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"][:2]] == [
        alpha_card.id,
        zeta_card.id,
    ]


def test_grouped_gallery_sort_uses_anchor_card_values() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Sort Group Zephyr Group")
    member_card, member_version = _create_editable_card_version(name="Sort Group Zephyr Member")
    standalone_card, standalone_version = _create_editable_card_version(
        name="Sort Group Amber Solo"
    )
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


def test_grouped_gallery_mana_family_sort_uses_the_anchor_card() -> None:
    arcane_mana = _get_or_create_symbol(key="arcane-mana", label="Arcane Mana", symbol_type="mana")
    dark_affinity = _get_or_create_symbol(
        key="dark-affinity", label="Dark Affinity", symbol_type="affinity"
    )
    group_anchor, anchor_version = _create_editable_card_version(name="Family Group Zeta Anchor")
    group_member, member_version = _create_editable_card_version(name="Family Group Alpha Member")
    standalone, standalone_version = _create_editable_card_version(
        name="Family Group Beta Standalone"
    )
    for version in (anchor_version, member_version, standalone_version):
        _create_card_image(version)
    replace_card_version_symbols(card_version_id=anchor_version.id, symbol_ids=[arcane_mana.id])
    replace_card_version_symbols(card_version_id=member_version.id, symbol_ids=[dark_affinity.id])
    replace_card_version_symbols(
        card_version_id=standalone_version.id, symbol_ids=[dark_affinity.id]
    )
    set_card_mana_families(card=group_anchor, mana_families=("arcane",))
    set_card_mana_families(card=group_member, mana_families=("dark",))
    set_card_mana_families(card=standalone, mana_families=("dark",))
    _create_card_group(
        "mana-family-sorted-group",
        anchor_card=group_anchor,
        members=[group_anchor, group_member],
    )

    response = Client(HTTP_HOST="localhost").get(
        "/cards",
        {"show_groups": "true", "sort": "mana_type_asc", "q": "Family Group"},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["result_type"] == "card_group"
    assert results[0]["anchor_card_id"] == group_anchor.id
    assert results[1]["result_type"] == "card"
    assert results[1]["id"] == standalone.id


def test_grouped_gallery_paginates_before_hydrating_payloads() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Paged Group Beta Anchor")
    member_card, member_version = _create_editable_card_version(name="Paged Group Beta Member")
    alpha_card, alpha_version = _create_editable_card_version(name="Paged Group Alpha Solo")
    zeta_card, zeta_version = _create_editable_card_version(name="Paged Group Zeta Solo")
    for version in (anchor_version, member_version, alpha_version, zeta_version):
        _create_card_image(version)
    _create_card_group(
        "paged-group-beta", anchor_card=anchor_card, members=[anchor_card, member_card]
    )

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
    standalone_card, standalone_version = _create_editable_card_version(
        name="Sort Type Group Creature Solo"
    )
    _filler_spell_card, filler_spell_version = _create_editable_card_version(
        name="Grouped Priority Spell Filler"
    )

    for version in (anchor_version, member_version, standalone_version, filler_spell_version):
        _create_card_image(version)

    replace_card_version_types(card_version_id=anchor_version.id, type_ids=[mana_type.id])
    replace_card_version_types(card_version_id=member_version.id, type_ids=[spell_type.id])
    replace_card_version_types(card_version_id=standalone_version.id, type_ids=[creature_type.id])
    replace_card_version_types(card_version_id=filler_spell_version.id, type_ids=[spell_type.id])
    _create_card_group(
        "sorted-type-group", anchor_card=anchor_card, members=[anchor_card, member_card]
    )

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


def test_grouped_gallery_default_sort_uses_anchor_card_values() -> None:
    anchor_card, anchor_version = _create_editable_card_version(
        name="Unmatched Default Group Anchor"
    )
    member_card, member_version = _create_editable_card_version(
        name="Default Group Matching Member"
    )
    standalone_card, standalone_version = _create_editable_card_version(
        name="Default Group Matching Standalone"
    )
    for version in (anchor_version, member_version, standalone_version):
        _create_card_image(version)
    set_card_mana_families(card=anchor_card, mana_families=("arcane",))
    set_card_mana_families(card=member_card, mana_families=("arcane",))
    set_card_mana_families(card=standalone_card, mana_families=("arcane",))
    anchor_version.mana_value = 0
    member_version.mana_value = 0
    standalone_version.mana_value = 9
    anchor_version.save(update_fields=["mana_value"])
    member_version.save(update_fields=["mana_value"])
    standalone_version.save(update_fields=["mana_value"])
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card=anchor_card, role="boss"),
            CardRoleAssignment(card=member_card, role="hero"),
        ]
    )
    _create_card_group(
        "default-anchor-sort-group",
        anchor_card=anchor_card,
        members=[anchor_card, member_card],
    )

    response = Client(HTTP_HOST="localhost").get(
        "/cards",
        {"show_groups": "true", "sort": "default", "q": "Default Group Matching"},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["result_type"] == "card"
    assert results[0]["id"] == standalone_card.id
    assert results[1]["result_type"] == "card_group"
    assert results[1]["anchor_card_id"] == anchor_card.id


def test_grouped_gallery_default_sort_uses_group_identity_for_shared_anchors() -> None:
    anchor_card, anchor_version = _create_editable_card_version(
        name="Duplicate Anchor Default Card"
    )
    _create_card_image(anchor_version)
    alpha_group = _create_card_group(
        "duplicate-anchor-alpha",
        anchor_card=anchor_card,
        members=[anchor_card],
    )
    zeta_group = _create_card_group(
        "duplicate-anchor-zeta",
        anchor_card=anchor_card,
        members=[anchor_card],
    )
    expected_ids = sorted([alpha_group.id, zeta_group.id])
    client = Client(HTTP_HOST="localhost")

    first_response = client.get(
        "/cards",
        {
            "show_groups": "true",
            "sort": "default",
            "q": "Duplicate Anchor Default",
            "page": 1,
            "page_size": 1,
        },
    )
    second_response = client.get(
        "/cards",
        {
            "show_groups": "true",
            "sort": "default",
            "q": "Duplicate Anchor Default",
            "page": 2,
            "page_size": 1,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["count"] == 2
    assert [
        first_response.json()["results"][0]["id"],
        second_response.json()["results"][0]["id"],
    ] == expected_ids


def test_export_cards_csv_honors_selected_sort() -> None:
    _zebra_card, zebra_version = _create_editable_card_version(name="Sort Export Zebra Export")
    _alpha_card, alpha_version = _create_editable_card_version(name="Sort Export Alpha Export")
    _create_card_image(zebra_version)
    _create_card_image(alpha_version)
    zebra_version.updated_at = timezone.now() - timedelta(days=1)
    alpha_version.updated_at = timezone.now()
    zebra_version.save(update_fields=["updated_at"])
    alpha_version.save(update_fields=["updated_at"])

    response = _staff_client("csv-export-sort-user").get(
        "/exports/csv", {"sort": "name_asc", "q": "Sort Export"}
    )

    assert response.status_code == 200
    rows = response.content.decode("utf-8").splitlines()
    assert rows[1].split(",")[1] == "Sort Export Alpha Export"
    assert rows[2].split(",")[1] == "Sort Export Zebra Export"


def test_export_cards_csv_honors_mana_family_sort() -> None:
    arcane_affinity = _get_or_create_symbol(
        key="arcane-affinity", label="Arcane Affinity", symbol_type="affinity"
    )
    dark_mana = _get_or_create_symbol(key="dark-mana", label="Dark Mana", symbol_type="mana")
    _dark_card, dark_version = _create_editable_card_version(name="Family Export Alpha Dark")
    _arcane_card, arcane_version = _create_editable_card_version(name="Family Export Zeta Arcane")
    _create_card_image(dark_version)
    _create_card_image(arcane_version)
    replace_card_version_symbols(card_version_id=dark_version.id, symbol_ids=[dark_mana.id])
    replace_card_version_symbols(card_version_id=arcane_version.id, symbol_ids=[arcane_affinity.id])
    set_card_mana_families(card=_dark_card, mana_families=("dark",))
    set_card_mana_families(card=_arcane_card, mana_families=("arcane",))

    response = _staff_client("csv-export-family-sort-user").get(
        "/exports/csv",
        {"sort": "mana_type_asc", "q": "Family Export"},
    )

    assert response.status_code == 200
    rows = response.content.decode("utf-8").splitlines()
    assert rows[1].split(",")[1] == "Family Export Zeta Arcane"
    assert rows[2].split(",")[1] == "Family Export Alpha Dark"


def test_card_detail_and_group_detail_include_card_group_membership() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Detail Anchor")
    member_card, member_version = _create_editable_card_version(name="Detail Member")
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    group = _create_card_group(
        "detail-group", anchor_card=anchor_card, members=[anchor_card, member_card]
    )

    client = Client(HTTP_HOST="localhost")
    card_response = client.get(f"/cards/{member_card.id}")
    group_response = client.get(f"/card-groups/{group.id}")

    assert card_response.status_code == 200
    assert group_response.status_code == 200
    card_payload = card_response.json()
    group_payload = group_response.json()
    assert card_payload["card_groups"][0]["id"] == group.id
    assert card_payload["card_groups"][0]["card_pool"] == "player"
    assert card_payload["card_groups"][0]["is_anchor"] is False
    assert group_payload["id"] == group.id
    assert [member["card"]["id"] for member in group_payload["members"]] == [
        anchor_card.id,
        member_card.id,
    ]
    assert group_payload["members"][0]["is_anchor"] is True


def test_cross_pool_group_relationships_only_expose_authorized_members() -> None:
    player_card, player_version = _create_editable_card_version(name="Cross Pool Group Player")
    evil_card, evil_version = _create_editable_card_version(name="Cross Pool Group Evil")
    evil_card.card_pool = "evil"
    evil_card.save(update_fields=["card_pool"])
    _create_card_image(player_version)
    _create_card_image(evil_version)
    group = _create_card_group(
        "cross-pool-detail-group",
        anchor_card=player_card,
        members=[player_card, evil_card],
    )

    anonymous_group_response = Client(HTTP_HOST="localhost").get(f"/card-groups/{group.id}")
    anonymous_card_response = Client(HTTP_HOST="localhost").get(f"/cards/{player_card.id}")
    staff_client = _staff_client("cross-pool-group-staff")
    staff_group_response = staff_client.get(f"/card-groups/{group.id}")
    staff_evil_card_response = staff_client.get(f"/cards/{evil_card.id}")

    assert anonymous_group_response.status_code == 200
    assert [member["card"]["id"] for member in anonymous_group_response.json()["members"]] == [
        player_card.id
    ]
    assert anonymous_card_response.json()["card_groups"][0]["id"] == group.id
    assert anonymous_card_response.json()["card_groups"][0]["member_count"] == 1
    assert anonymous_card_response.json()["card_groups"][0]["card_ids"] == [player_card.id]
    assert staff_group_response.status_code == 200
    assert [member["card"]["id"] for member in staff_group_response.json()["members"]] == [
        player_card.id,
        evil_card.id,
    ]
    assert staff_group_response.json()["members"][1]["card"]["card_pool"] == "evil"
    assert staff_evil_card_response.json()["card_groups"][0]["id"] == group.id
    assert staff_evil_card_response.json()["card_groups"][0]["card_pool"] == "player"
    assert staff_evil_card_response.json()["card_groups"][0]["member_count"] == 2
    assert staff_evil_card_response.json()["card_groups"][0]["card_ids"] == [
        player_card.id,
        evil_card.id,
    ]
    assert staff_evil_card_response.json()["card_groups"][0]["position"] == 2


def test_card_detail_includes_viewer_visible_deck_references() -> None:
    owner = _create_user("card-deck-reference-owner", "password", is_staff=False)
    other_owner = _create_user("card-deck-reference-other", "password", is_staff=False)
    hero_card, _hero_version = _create_editable_card_version(name="Deck Reference Hero")
    card, version = _create_editable_card_version(name="Deck Reference Included")
    _create_card_image(version)
    CardRoleAssignment.objects.create(card=hero_card, role="hero")
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
    assert references[0]["card_reference"]["as_hero"] is False
    assert references[0]["card_reference"]["mainboard_quantity"] == 2
    assert references[0]["card_reference"]["sideboard_quantity"] == 0
    assert anonymous_response.status_code == 200
    assert anonymous_response.json()["deck_references"] == []


def test_card_detail_limits_deck_references_to_three_latest() -> None:
    owner = _create_user("card-deck-reference-limit-owner", "password", is_staff=False)
    hero_card, _hero_version = _create_editable_card_version(name="Deck Reference Limit Hero")
    card, version = _create_editable_card_version(name="Deck Reference Limit Included")
    _create_card_image(version)
    CardRoleAssignment.objects.create(card=hero_card, role="hero")
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
    assert [reference["id"] for reference in references] == [
        deck.id for deck in reversed(decks[-3:])
    ]


def test_card_group_detail_includes_anchor_viewer_visible_deck_references() -> None:
    owner = _create_user("group-deck-reference-owner", "password", is_staff=False)
    other_owner = _create_user("group-deck-reference-other", "password", is_staff=False)
    anchor_card, anchor_version = _create_editable_card_version(name="Group Deck Reference Anchor")
    member_card, member_version = _create_editable_card_version(name="Group Deck Reference Member")
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    CardRoleAssignment.objects.create(card=anchor_card, role="hero")
    group = _create_card_group(
        "group-deck-reference", anchor_card=anchor_card, members=[anchor_card, member_card]
    )
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
    assert references[0]["card_reference"]["as_hero"] is True
    assert references[0]["card_reference"]["mainboard_quantity"] == 0
    assert references[0]["card_reference"]["sideboard_quantity"] == 0
    assert anonymous_response.status_code == 200
    assert anonymous_response.json()["anchor_deck_references"] == []


def test_card_group_detail_limits_anchor_deck_references_to_three_latest() -> None:
    owner = _create_user("group-deck-reference-limit-owner", "password", is_staff=False)
    anchor_card, anchor_version = _create_editable_card_version(
        name="Group Deck Reference Limit Anchor"
    )
    member_card, member_version = _create_editable_card_version(
        name="Group Deck Reference Limit Member"
    )
    _create_card_image(anchor_version)
    _create_card_image(member_version)
    CardRoleAssignment.objects.create(card=anchor_card, role="hero")
    group = _create_card_group(
        "group-deck-reference-limit", anchor_card=anchor_card, members=[anchor_card, member_card]
    )
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
    assert [reference["id"] for reference in references] == [
        deck.id for deck in reversed(decks[-3:])
    ]


def test_public_card_group_detail_hides_deprecated_linked_cards_by_default() -> None:
    anchor_card, anchor_version = _create_editable_card_version(name="Detail Lifecycle Anchor")
    deprecated_card, deprecated_version = _create_editable_card_version(
        name="Detail Lifecycle Deprecated"
    )
    _create_card_image(anchor_version)
    _create_card_image(deprecated_version)
    deprecated_card.lifecycle_status = "deprecated"
    deprecated_card.save(update_fields=["lifecycle_status"])
    group = _create_card_group(
        "detail-lifecycle-group", anchor_card=anchor_card, members=[anchor_card, deprecated_card]
    )

    client = Client(HTTP_HOST="localhost")
    default_response = client.get(f"/card-groups/{group.id}")
    all_response = client.get(f"/card-groups/{group.id}", {"lifecycle_status": "all"})

    assert default_response.status_code == 200
    assert all_response.status_code == 200
    assert default_response.json()["member_count"] == 1
    assert [member["card"]["id"] for member in default_response.json()["members"]] == [
        anchor_card.id
    ]
    assert all_response.json()["member_count"] == 2
    assert [member["card"]["id"] for member in all_response.json()["members"]] == [
        anchor_card.id,
        deprecated_card.id,
    ]


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
    _create_card_group(
        "lifecycle-anchor-guard", anchor_card=anchor_card, members=[anchor_card, member_card]
    )

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


def test_card_group_management_rejects_deprecated_anchor_but_allows_deprecated_member() -> None:
    username = "staff-deprecated-anchor-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    active_anchor, _active_version = _create_editable_card_version(name="Group Active Anchor")
    active_member, _member_version = _create_editable_card_version(name="Group Active Member")
    deprecated_card, _deprecated_version = _create_editable_card_version(
        name="Group Deprecated Candidate"
    )
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


def test_staff_can_manage_card_groups() -> None:
    username = "staff-card-groups-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    anchor_card, _anchor_version = _create_editable_card_version(name="Staff Group Anchor")
    member_card, _member_version = _create_editable_card_version(name="Staff Group Member")
    replacement_card, _replacement_version = _create_editable_card_version(
        name="Staff Group Replacement"
    )
    member_card.card_pool = "evil"
    member_card.save(update_fields=["card_pool"])
    CardFactionAssignment.objects.create(card=member_card, faction="dark")

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
    assert [member["card_id"] for member in patch_response.json()["members"]] == [
        replacement_card.id,
        member_card.id,
    ]
    assert [member["card_pool"] for member in patch_response.json()["members"]] == [
        "player",
        "evil",
    ]
    assert [member["card_factions"] for member in patch_response.json()["members"]] == [
        [],
        ["dark"],
    ]
    assert all(row["id"] != group_id for row in client.get("/admin/card-groups").json())


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
    assert CardAlias.objects.filter(
        card_id=target_card.id,
        card_pool="player",
        key=source_card.key,
    ).exists()
    assert CardMergeRedirect.objects.filter(
        old_card_id=source_card.id, target_card_id=target_card.id
    ).exists()
    assert list(
        CardVersion.objects.filter(card_id=target_card.id)
        .order_by("version_number")
        .values_list("id", flat=True)
    ) == [
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


def test_card_merge_rejects_cross_pool_sources() -> None:
    target_card, _target_version = _create_editable_card_version(name="Cross Pool Merge Target")
    source_card, _source_version = _create_editable_card_version(name="Cross Pool Merge Source")
    source_card.card_pool = "neutral"
    source_card.save(update_fields=["card_pool"])
    username = "staff-cross-pool-merge-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)
    payload = {"target_card_id": target_card.id, "source_card_ids": [source_card.id]}

    preview = client.post(
        "/admin/card-merges/preview",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    apply = client.post(
        "/admin/card-merges/apply",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert preview.status_code == 200
    assert preview.json()["can_apply"] is False
    assert "Cards from different pools cannot be merged." in preview.json()["blocking_conflicts"]
    assert apply.status_code == 400
    assert Card.objects.filter(id__in=[target_card.id, source_card.id]).count() == 2


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
    CardAlias.objects.create(
        card=target_card,
        card_pool=target_card.card_pool,
        key="old-import-card",
        label="Old Import Card",
    )
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
    source_file = resolve_storage_path(
        build_storage_relative_path("uploads", "content-version-card.png")
    )
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
    card, target_version = _create_editable_card_version(name="Content Version Reparse")
    set_card_mana_families(card=card, mana_families=("arcane",))
    primal_symbol = _get_or_create_symbol(
        key="primal-affinity",
        label="Primal Affinity",
        symbol_type="affinity",
    )
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
        symbol_ids=[primal_symbol.id],
        reparse_existing=False,
    )

    assert version.id == target_version.id
    assert version.content_version == original_content_version
    card.refresh_from_db()
    assert card.mana_family_sort_key == 0


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
    target_version.save(
        update_fields=["content_version", "image_hash", "name", "field_sources_json"]
    )
    replace_card_version_tags(card_version_id=target_version.id, tag_ids=[manual_tag.id])
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "content-version-snapshot.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        content_version=next_content_version,
        total_items=1,
    )
    source_file = resolve_storage_path(
        build_storage_relative_path("uploads", "content-version-snapshot.png")
    )
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


def test_import_assigns_resolved_pool_roles_and_evidence_to_new_card() -> None:
    source_file = settings.storage_root_dir / "uploads" / "classified-new-card.png"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"classified-new-card")
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "classified-new-card.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        card_pool="evil",
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "classified-new-card.png"),
    )

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="classified-new-card-checksum",
        normalized_fields={"name": "Classified New Card"},
        confidence={"overall": 0.8},
        raw_ocr={},
        reparse_existing=False,
        card_pool="evil",
        resolved_card_roles=("hero", "event"),
        resolved_card_factions=("order", "dark", "metal"),
        resolved_card_mana_families=("arcane", "dark"),
        classification_evidence={
            "roles": {
                "mode": "automatic",
                "matched_tag_sources": [{"id": "tag-hero", "key": "hero"}],
                "matched_type_sources": [],
                "matched_symbol_sources": [],
                "matched_rules": [],
                "override_roles": [],
                "resolved_roles": ["hero", "event"],
                "snapshot_digest": "test-digest",
            },
            "factions": {
                "mode": "automatic",
                "matched_tag_sources": [
                    {"id": "tag-order", "key": "order"},
                    {"id": "tag-dark", "key": "dark"},
                    {"id": "tag-metal", "key": "metal"},
                ],
                "matched_type_sources": [],
                "matched_symbol_sources": [],
                "matched_rules": [],
                "override_factions": [],
                "resolved_factions": ["order", "dark", "metal"],
                "snapshot_digest": "test-digest",
            },
            "mana_families": {
                "mode": "automatic",
                "matched_tag_sources": [],
                "matched_type_sources": [],
                "matched_symbol_sources": [
                    {"id": "symbol-arcane", "key": "arcane-mana"},
                    {"id": "symbol-dark", "key": "dark-affinity"},
                ],
                "matched_rules": [],
                "override_mana_families": [],
                "resolved_mana_families": ["arcane", "dark"],
                "snapshot_digest": "test-digest",
            },
        },
    )

    item.refresh_from_db()
    assert version.card.card_pool == "evil"
    assert list(version.card.role_assignments.order_by("role").values_list("role", flat=True)) == [
        "event",
        "hero",
    ]
    assert list(
        version.card.faction_assignments.order_by("faction").values_list("faction", flat=True)
    ) == ["dark", "metal", "order"]
    assert item.status == "completed"
    assert item.resolved_card_roles_json == ["hero", "event"]
    assert item.resolved_card_factions_json == ["order", "dark", "metal"]
    assert item.resolved_card_mana_families_json == ["arcane", "dark"]
    assert set(
        version.card.mana_family_assignments.values_list("mana_family", flat=True)
    ) == {"arcane", "dark"}
    assert item.classification_inference_json["roles"]["matched_tag_sources"] == [
        {"id": "tag-hero", "key": "hero"}
    ]


def test_classification_mismatch_preserves_existing_card_and_coexists_with_lifecycle_warning() -> (
    None
):
    card, target_version = _create_editable_card_version(name="Classification Mismatch Card")
    card.lifecycle_status = "deprecated"
    card.card_pool = "evil"
    card.save(update_fields=["lifecycle_status", "card_pool"])
    set_card_mana_families(card=card, mana_families=("arcane",))
    source_file = settings.storage_root_dir / "uploads" / "classification-mismatch.png"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"classification-mismatch")
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "classification-mismatch.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        card_pool="evil",
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "classification-mismatch.png"),
    )

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="classification-mismatch-checksum",
        normalized_fields={"name": "Classification Mismatch Card"},
        confidence={"overall": 0.8},
        raw_ocr={},
        reparse_existing=False,
        card_pool="evil",
        resolved_card_roles=("event",),
        resolved_card_mana_families=("dark",),
        classification_evidence={
            "roles": {
                "mode": "automatic",
                "matched_tag_sources": [],
                "matched_type_sources": [],
                "matched_symbol_sources": [],
                "matched_rules": [],
                "override_roles": [],
                "resolved_roles": ["event"],
                "snapshot_digest": "test-digest",
            },
            "factions": {
                "mode": "automatic",
                "matched_tag_sources": [],
                "matched_type_sources": [],
                "matched_symbol_sources": [],
                "matched_rules": [],
                "override_factions": [],
                "resolved_factions": [],
                "snapshot_digest": "test-digest",
            },
            "mana_families": {
                "mode": "automatic",
                "matched_tag_sources": [],
                "matched_type_sources": [],
                "matched_symbol_sources": [
                    {"id": "symbol-dark", "key": "dark-mana"}
                ],
                "matched_rules": [],
                "override_mana_families": [],
                "resolved_mana_families": ["dark"],
                "snapshot_digest": "test-digest",
            },
        },
    )

    card.refresh_from_db()
    item.refresh_from_db()
    assert version.card == card
    assert version.version_number == target_version.version_number + 1
    assert card.card_pool == "evil"
    assert not card.role_assignments.exists()
    assert list(card.mana_family_assignments.values_list("mana_family", flat=True)) == [
        "arcane"
    ]
    assert item.status == "completed"
    assert [warning["code"] for warning in item.warnings_json] == [
        "matched_deprecated_card",
        "card_classification_mismatch",
    ]
    mismatch = next(
        warning
        for warning in item.warnings_json
        if warning["code"] == "card_classification_mismatch"
    )
    assert mismatch["details"]["stored"]["card_mana_families"] == ["arcane"]
    assert mismatch["details"]["live"]["card_mana_families"] == ["arcane"]
    assert mismatch["details"]["inferred"]["card_mana_families"] == ["dark"]
    assert item.classification_inference_json["mana_families"][
        "matched_symbol_sources"
    ] == [{"id": "symbol-dark", "key": "dark-mana"}]


def test_untargeted_import_does_not_match_same_name_or_image_hash_across_pools() -> None:
    player_card, player_version = _create_editable_card_version(name="Cross Pool Twin")
    player_version.image_hash = "cross-pool-shared-checksum"
    player_version.save(update_fields=["image_hash"])
    source_file = settings.storage_root_dir / "uploads" / "cross-pool-twin.png"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"cross-pool-twin")
    job = ImportJob.objects.create(
        source_path=build_storage_relative_path("uploads", "cross-pool-twin.png"),
        template=Template.objects.get(key="mtg-like-v1"),
        card_pool="neutral",
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file=build_storage_relative_path("uploads", "cross-pool-twin.png"),
    )

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="cross-pool-shared-checksum",
        normalized_fields={"name": "Cross Pool Twin"},
        confidence={"overall": 0.8},
        raw_ocr={},
        card_pool="neutral",
        resolved_card_roles=("location",),
    )

    item.refresh_from_db()
    assert version.card_id != player_card.id
    assert version.card.card_pool == "neutral"
    assert version.card.key == player_card.key
    assert list(version.card.role_assignments.values_list("role", flat=True)) == ["location"]
    assert item.warnings_json == []


def test_targeted_reparse_rolls_back_name_conflict() -> None:
    card, version = _create_editable_card_version(name="Rollback Target")
    _conflicting_card, _conflicting_version = _create_editable_card_version(
        name="Rollback Conflict"
    )
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


def test_seed_users_updates_existing_user_password(
    tmp_path: Path,
) -> None:
    seed_path = tmp_path / "seed-users.json"
    seed_path.write_text(
        """
        {
          "users": [
            {
              "username": "existing-seed-user",
              "password": "updated-seed-password",
              "is_staff": true,
              "is_superuser": true
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    get_user_model().objects.filter(username="existing-seed-user").delete()
    existing_user = get_user_model().objects.create_user(
        username="existing-seed-user",
        password="old-seed-password",
        is_staff=False,
        is_superuser=False,
    )

    result = seed_users(seed_path)

    existing_user.refresh_from_db()
    assert result.created == 0
    assert result.existing == 1
    assert existing_user.check_password("updated-seed-password")
    assert existing_user.is_staff is True
    assert existing_user.is_superuser is True


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
    version.save(
        update_fields=["rules_text", "type_line", "field_sources_json", "parsed_snapshot_json"]
    )

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


def _staff_client(username: str) -> Client:
    user = _create_user(username, "password", is_staff=True)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    return client


def _get_or_create_symbol(*, key: str, label: str, symbol_type: str) -> Symbol:
    symbol, _created = Symbol.objects.get_or_create(
        key=key,
        defaults={
            "label": label,
            "symbol_type": symbol_type,
            "detector_type": "template",
            "detection_config_json": {},
            "text_enrichment_json": {},
            "reference_assets_json": [],
            "enabled": True,
        },
    )
    return symbol


def _create_editable_card_version(
    *, name: str, card_pool: str = "player"
) -> tuple[Card, CardVersion]:
    from card_reader_core.models import Template

    template = Template.objects.get(key="mtg-like-v1")
    card = Card.objects.create(
        key=name.lower().replace(" ", "-"),
        label=name,
        card_pool=card_pool,
    )
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

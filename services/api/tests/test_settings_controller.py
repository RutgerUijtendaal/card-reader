from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from PIL import Image

from card_reader_api.catalog.assets import store_symbol_asset
from card_reader_api.maintenance import services as maintenance_services
from card_reader_api.maintenance.services import MaintenanceService
from card_reader_core.models import Card, CardGroup, CardVersion, CardVersionImage, Deck, DeckEntry, ImportJob, ImportJobItem, Template
from card_reader_core.services.cards import convert_card_images_to_webp
from card_reader_core.services.templates import TemplateService
from card_reader_core.config.settings import settings
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path


def _template_definition(region_id: str) -> dict[str, object]:
    return {
        "id": region_id,
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


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color=(20, 120, 200)).save(path, format="PNG")


def _create_image_record(
    *,
    stored_path: str,
    checksum: str = "image-checksum",
    source_file: str | None = None,
) -> CardVersionImage:
    template = Template.objects.create(
        key=f"image-template-{checksum}",
        label="Image Template",
        definition_json=_template_definition("top_bar"),
    )
    card = Card.objects.create(key=f"image-card-{checksum}", label="Image Card")
    version = CardVersion.objects.create(
        card=card,
        version_number=1,
        template=template,
        image_hash=checksum,
        name="Image Card",
        is_latest=True,
    )
    return CardVersionImage.objects.create(
        card_version=version,
        source_file=source_file or stored_path,
        stored_path=stored_path,
        checksum=checksum,
    )


def test_upload_symbol_asset_stores_under_uploads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    upload = SimpleUploadedFile("Fire Mana.PNG", BytesIO(b"symbol-asset").read())

    stored_path = store_symbol_asset(upload, "Fire Mana.PNG", ".png")
    relative_path = f"uploads/{stored_path.name}"

    assert relative_path.startswith("uploads/fire-mana-")
    assert relative_path.endswith(".png")
    assert not relative_path.startswith("symbols/")

    assert stored_path.parent == tmp_path / "symbols" / "uploads"
    assert stored_path.read_bytes() == b"symbol-asset"


def test_convert_card_images_to_webp_updates_paths_and_keeps_original(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    CardVersionImage.objects.all().delete()

    source_path = resolve_storage_path("images/image-checksum.png")
    _write_png(source_path)
    image = _create_image_record(stored_path="images/image-checksum.png")

    result = convert_card_images_to_webp()

    image.refresh_from_db()
    assert result.converted == 1
    assert result.already_webp == 0
    assert result.missing == 0
    assert result.failed == 0
    assert image.stored_path == "images/image-checksum.webp"
    assert source_path.exists()
    with Image.open(resolve_storage_path(image.stored_path)) as converted:
        assert converted.format == "WEBP"


def test_convert_card_images_to_webp_reports_missing_without_updates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    CardVersionImage.objects.all().delete()
    image = _create_image_record(stored_path="images/missing-image.png", checksum="missing-image")

    result = convert_card_images_to_webp()

    image.refresh_from_db()
    assert result.converted == 0
    assert result.missing == 1
    assert result.failed == 0
    assert image.stored_path == "images/missing-image.png"


def test_convert_card_images_to_webp_repairs_missing_stored_path_from_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    CardVersionImage.objects.all().delete()

    source_path = resolve_storage_path("uploads/source-image.png")
    _write_png(source_path)
    image = _create_image_record(
        source_file="uploads/source-image.png",
        stored_path="images/missing-source-image.png",
        checksum="source-image",
    )

    result = convert_card_images_to_webp()

    image.refresh_from_db()
    assert result.converted == 1
    assert result.missing == 0
    assert result.failed == 0
    assert image.stored_path == "images/source-image.webp"
    assert source_path.exists()
    with Image.open(resolve_storage_path(image.stored_path)) as converted:
        assert converted.format == "WEBP"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_convert_card_images_to_webp_endpoint_returns_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    CardVersionImage.objects.all().delete()

    source_path = resolve_storage_path("images/endpoint-image.png")
    _write_png(source_path)
    _create_image_record(stored_path="images/endpoint-image.png", checksum="endpoint-image")

    user = get_user_model().objects.create_user(
        username="webp-conversion-superuser",
        password="password",
        is_staff=True,
        is_superuser=True,
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)

    response = client.post(
        "/admin/maintenance/convert-card-images-to-webp",
        data={},
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["converted"] == 1
    assert payload["already_webp"] == 0
    assert payload["missing"] == 0
    assert payload["failed"] == 0
    assert payload["bytes_before"] > payload["bytes_after"]
def test_queue_reparse_latest_versions_groups_jobs_by_template(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)

    image_a = resolve_storage_path("images/image-a.webp")
    image_b = resolve_storage_path("images/image-b.webp")
    image_c = resolve_storage_path("images/image-c.webp")
    for image_path in [image_a, image_b, image_c]:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"image")

    ImportJobItem.objects.all().delete()
    ImportJob.objects.all().delete()
    DeckEntry.objects.all().delete()
    Deck.objects.all().delete()
    CardVersionImage.objects.all().delete()
    CardVersion.objects.all().delete()
    CardGroup.objects.all().delete()
    Card.objects.all().delete()
    Template.objects.filter(key__in=["mtg-like-v1", "sorcery-v1"]).delete()

    mtg_template = Template.objects.create(
        key="mtg-like-v1",
        label="MTG",
        definition_json=_template_definition("top_bar"),
    )
    sorcery_template = Template.objects.create(
        key="sorcery-v1",
        label="Sorcery",
        definition_json=_template_definition("top_bar_alt"),
    )

    card_a = Card.objects.create(key="card-a", label="Card A")
    card_b = Card.objects.create(key="card-b", label="Card B")
    card_c = Card.objects.create(key="card-c", label="Card C")

    version_a = CardVersion.objects.create(
        card_id=card_a.id,
        version_number=1,
        template=mtg_template,
        image_hash="hash-a",
        name="Card A",
        is_latest=True,
    )
    version_b = CardVersion.objects.create(
        card_id=card_b.id,
        version_number=1,
        template=mtg_template,
        image_hash="hash-b",
        name="Card B",
        is_latest=True,
    )
    version_c = CardVersion.objects.create(
        card_id=card_c.id,
        version_number=1,
        template=sorcery_template,
        image_hash="hash-c",
        name="Card C",
        is_latest=True,
    )

    card_a.latest_version_id = version_a.id
    card_b.latest_version_id = version_b.id
    card_c.latest_version_id = version_c.id
    card_a.save(update_fields=["latest_version"])
    card_b.save(update_fields=["latest_version"])
    card_c.save(update_fields=["latest_version"])

    CardVersionImage.objects.create(
        card_version_id=version_a.id,
        source_file=build_storage_relative_path("images", image_a.name),
        stored_path=build_storage_relative_path("images", image_a.name),
        checksum="hash-a",
    )
    CardVersionImage.objects.create(
        card_version_id=version_b.id,
        source_file=build_storage_relative_path("images", image_b.name),
        stored_path=build_storage_relative_path("images", image_b.name),
        checksum="hash-b",
    )
    CardVersionImage.objects.create(
        card_version_id=version_c.id,
        source_file=build_storage_relative_path("images", image_c.name),
        stored_path=build_storage_relative_path("images", image_c.name),
        checksum="hash-c",
    )

    result = MaintenanceService().queue_reparse_latest_versions()

    jobs = list(ImportJob.objects.select_related("template").order_by("template__key"))
    items = list(ImportJobItem.objects.order_by("source_file"))

    assert "Queued 2 reparse jobs for 3 latest card images." == result.message
    assert result.removed_paths == []
    assert len(jobs) == 2
    assert {job.template.key for job in jobs} == {"mtg-like-v1", "sorcery-v1"}
    assert all(job.total_items >= 1 for job in jobs)
    assert {item.source_file for item in items} == {
        build_storage_relative_path("images", image_a.name),
        build_storage_relative_path("images", image_b.name),
        build_storage_relative_path("images", image_c.name),
    }
    assert {(item.target_card_id, item.target_card_version_id) for item in items} == {
        (card_a.id, version_a.id),
        (card_b.id, version_b.id),
        (card_c.id, version_c.id),
    }


def test_queue_reparse_latest_versions_by_filters_targets_only_matching_cards(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)

    image_a = resolve_storage_path("images/filtered-image-a.webp")
    image_b = resolve_storage_path("images/filtered-image-b.webp")
    for image_path in [image_a, image_b]:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"image")

    ImportJobItem.objects.all().delete()
    ImportJob.objects.all().delete()
    DeckEntry.objects.all().delete()
    Deck.objects.all().delete()
    CardVersionImage.objects.all().delete()
    CardVersion.objects.all().delete()
    CardGroup.objects.all().delete()
    Card.objects.all().delete()
    Template.objects.filter(key="mtg-like-v1").delete()

    template = Template.objects.create(
        key="mtg-like-v1",
        label="MTG",
        definition_json=_template_definition("top_bar"),
    )

    alpha_card = Card.objects.create(key="alpha-card", label="Alpha Card")
    beta_card = Card.objects.create(key="beta-card", label="Beta Card")

    alpha_version = CardVersion.objects.create(
        card_id=alpha_card.id,
        version_number=1,
        template=template,
        image_hash="filtered-a",
        name="Alpha Card",
        is_latest=True,
    )
    beta_version = CardVersion.objects.create(
        card_id=beta_card.id,
        version_number=1,
        template=template,
        image_hash="filtered-b",
        name="Beta Card",
        is_latest=True,
    )

    alpha_card.latest_version_id = alpha_version.id
    beta_card.latest_version_id = beta_version.id
    alpha_card.save(update_fields=["latest_version"])
    beta_card.save(update_fields=["latest_version"])

    CardVersionImage.objects.create(
        card_version_id=alpha_version.id,
        source_file=build_storage_relative_path("images", image_a.name),
        stored_path=build_storage_relative_path("images", image_a.name),
        checksum="filtered-a",
    )
    CardVersionImage.objects.create(
        card_version_id=beta_version.id,
        source_file=build_storage_relative_path("images", image_b.name),
        stored_path=build_storage_relative_path("images", image_b.name),
        checksum="filtered-b",
    )

    result = MaintenanceService().queue_reparse_latest_versions_by_filters(
        filters={
            "query": "Alpha",
            "card_ids": None,
            "max_confidence": None,
            "keyword_ids": None,
            "keyword_match": None,
            "tag_ids": None,
            "tag_match": None,
            "mana_symbol_ids": None,
            "mana_symbol_exclude_ids": None,
            "mana_symbol_match": None,
            "affinity_symbol_ids": None,
            "affinity_symbol_exclude_ids": None,
            "affinity_symbol_match": None,
            "devotion_symbol_ids": None,
            "devotion_symbol_exclude_ids": None,
            "devotion_symbol_match": None,
            "other_symbol_ids": None,
            "other_symbol_exclude_ids": None,
            "other_symbol_match": None,
            "symbol_ids": None,
            "type_ids": None,
            "type_match": None,
            "mana_cost_min": None,
            "mana_cost_max": None,
            "template_id": None,
            "is_hero": None,
            "attack_min": None,
            "attack_max": None,
            "health_min": None,
            "health_max": None,
            "sort": "updated_desc",
        }
    )

    jobs = list(ImportJob.objects.order_by("created_at"))
    items = list(ImportJobItem.objects.order_by("created_at"))

    assert result.message == "Queued 1 reparse job for 1 latest card image matching the selected filters."
    assert len(jobs) == 1
    assert jobs[0].template.key == template.key
    assert len(items) == 1
    assert items[0].target_card_id == alpha_card.id
    assert items[0].target_card_version_id == alpha_version.id


def test_template_reparse_endpoint_queues_matching_latest_versions(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)

    source_template = Template.objects.create(
        key="template-reparse-source",
        label="Template Reparse Source",
        definition_json=_template_definition("source_top_bar"),
    )
    target_template = Template.objects.create(
        key="template-reparse-target",
        label="Template Reparse Target",
        definition_json=_template_definition("target_top_bar"),
    )
    other_template = Template.objects.create(
        key="template-reparse-other",
        label="Template Reparse Other",
        definition_json=_template_definition("other_top_bar"),
    )

    card_a = Card.objects.create(key="template-card-a", label="Template Card A")
    card_b = Card.objects.create(key="template-card-b", label="Template Card B")

    version_a = CardVersion.objects.create(
        card_id=card_a.id,
        version_number=1,
        template=source_template,
        image_hash="template-a",
        name="Template Card A",
        is_latest=True,
    )
    version_b = CardVersion.objects.create(
        card_id=card_b.id,
        version_number=1,
        template=other_template,
        image_hash="template-b",
        name="Template Card B",
        is_latest=True,
    )
    card_a.latest_version_id = version_a.id
    card_b.latest_version_id = version_b.id
    card_a.save(update_fields=["latest_version"])
    card_b.save(update_fields=["latest_version"])

    image_a = resolve_storage_path("images/template-reparse-a.webp")
    image_b = resolve_storage_path("images/template-reparse-b.webp")
    for image_path in [image_a, image_b]:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"image")
    CardVersionImage.objects.create(
        card_version_id=version_a.id,
        source_file=build_storage_relative_path("images", image_a.name),
        stored_path=build_storage_relative_path("images", image_a.name),
        checksum="template-a",
    )
    CardVersionImage.objects.create(
        card_version_id=version_b.id,
        source_file=build_storage_relative_path("images", image_b.name),
        stored_path=build_storage_relative_path("images", image_b.name),
        checksum="template-b",
    )

    username = "staff-template-reparse-user"
    password = "password"
    user_model = get_user_model()
    user_model.objects.filter(username=username).delete()
    user = user_model.objects.create_user(username=username, password=password)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        content_type="application/json",
    ).json()["csrf_token"]

    response = client.post(
        f"/admin/templates/{target_template.id}/reparse",
        data={"source_template_id": source_template.key},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 202
    job = ImportJob.objects.order_by("-created_at").first()
    assert job is not None
    assert job.template.key == target_template.key
    items = list(ImportJobItem.objects.filter(job_id=job.id))
    assert len(items) == 1
    assert items[0].target_card_id == card_a.id
    assert items[0].target_card_version_id == version_a.id


def test_backfill_metadata_suggestions_runs_management_command(monkeypatch) -> None:
    recorded_calls: list[tuple[str, int]] = []

    def fake_call_command(name: str, verbosity: int = 1) -> None:
        recorded_calls.append((name, verbosity))

    monkeypatch.setattr(maintenance_services, "call_command", fake_call_command)

    result = MaintenanceService().backfill_metadata_suggestions()

    assert recorded_calls == [("backfill_metadata_suggestions", 0)]
    assert result.message == "Metadata suggestions backfill completed."
    assert result.removed_paths == []


def test_default_template_seed_uses_region_handler_schema() -> None:
    template = Template.objects.create(
        key="default-template-schema-test",
        label="Default Template Schema Test",
        definition_json={
            "id": "mtg-like-v1",
            "version": 7,
            "regions": [
                {
                    "region_id": "top_bar",
                    "parser_type": "name_mana_cost",
                    "cut_region": {"unit": "relative", "x": 0.04, "y": 0.02, "w": 0.92, "h": 0.07},
                    "ocr_config": {},
                },
                {
                    "region_id": "type_bar",
                    "parser_type": "type_tag",
                    "cut_region": {"unit": "relative", "x": 0.04, "y": 0.54, "w": 0.92, "h": 0.05},
                    "ocr_config": {},
                },
                {
                    "region_id": "rules_text",
                    "parser_type": "rules_text",
                    "cut_region": {"unit": "relative", "x": 0.07, "y": 0.6, "w": 0.86, "h": 0.32},
                    "ocr_config": {},
                },
                {
                    "region_id": "rules_text_fallback",
                    "parser_type": "rules_text",
                    "cut_region": {"unit": "relative", "x": 0.07, "y": 0.7, "w": 0.86, "h": 0.12},
                    "ocr_config": {},
                },
                {
                    "region_id": "bottom_left",
                    "parser_type": "attack",
                    "cut_region": {"unit": "relative", "x": 0.01, "y": 0.9, "w": 0.14, "h": 0.09},
                    "ocr_config": {},
                },
                {
                    "region_id": "bottom_middle",
                    "parser_type": "affinity",
                    "cut_region": {"unit": "relative", "x": 0.37, "y": 0.93, "w": 0.26, "h": 0.06},
                    "ocr_config": {},
                },
                {
                    "region_id": "bottom_right",
                    "parser_type": "health",
                    "cut_region": {"unit": "relative", "x": 0.85, "y": 0.9, "w": 0.14, "h": 0.08},
                    "ocr_config": {},
                },
            ],
        },
    )
    validated = TemplateService()._validate_template_definition(template.definition_json)
    assert validated["version"] == 7
    assert [region["parser_type"] for region in validated["regions"]] == [
        "name_mana_cost",
        "type_tag",
        "rules_text",
        "rules_text",
        "attack",
        "affinity",
        "health",
    ]

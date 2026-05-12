from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile

from card_reader_api.catalog.views import _store_symbol_asset
from card_reader_api.maintenance import services as maintenance_services
from card_reader_api.maintenance.services import MaintenanceService
from card_reader_core.models import Card, CardVersion, CardVersionImage, ImportJob, ImportJobItem, Template
from card_reader_core.settings import settings


def test_upload_symbol_asset_stores_under_uploads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    upload = SimpleUploadedFile("Fire Mana.PNG", BytesIO(b"symbol-asset").read())

    stored_path = _store_symbol_asset(upload, "Fire Mana.PNG", ".png")
    relative_path = f"uploads/{stored_path.name}"

    assert relative_path.startswith("uploads/fire-mana-")
    assert relative_path.endswith(".png")
    assert not relative_path.startswith("symbols/")

    assert stored_path.parent == tmp_path / "symbols" / "uploads"
    assert stored_path.read_bytes() == b"symbol-asset"


def test_clear_storage_preserves_active_logs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    logs_dir = tmp_path / "logs"
    uploads_dir = tmp_path / "uploads"
    debug_dir = tmp_path / "debug-crops"
    images_dir = tmp_path / "images"
    for directory in [logs_dir, uploads_dir, debug_dir, images_dir]:
        directory.mkdir(parents=True)
        (directory / "sample.txt").write_text("data", encoding="utf-8")

    result = MaintenanceService().clear_storage_data(include_images=True)

    assert str(logs_dir) not in result.removed_paths
    assert (logs_dir / "sample.txt").exists()
    assert not (uploads_dir / "sample.txt").exists()
    assert not (debug_dir / "sample.txt").exists()
    assert images_dir.exists()
    assert not (images_dir / "sample.txt").exists()


def test_database_reset_uses_schema_drop_without_deleting_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "card_reader.db"
    database_path.write_text("locked", encoding="utf-8")
    dropped = False

    def fake_drop_schema() -> None:
        nonlocal dropped
        dropped = True

    monkeypatch.setattr(maintenance_services, "DATABASE_PATH", database_path)
    monkeypatch.setattr(MaintenanceService, "_drop_database_schema", staticmethod(fake_drop_schema))

    removed_paths = MaintenanceService()._reset_database()

    assert dropped
    assert removed_paths == [f"{database_path} (schema reset)"]
    assert database_path.exists()


def test_queue_reparse_latest_versions_groups_jobs_by_template(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)

    image_a = tmp_path / "image-a.webp"
    image_b = tmp_path / "image-b.webp"
    image_c = tmp_path / "image-c.webp"
    for image_path in [image_a, image_b, image_c]:
        image_path.write_bytes(b"image")

    ImportJobItem.objects.all().delete()
    ImportJob.objects.all().delete()
    CardVersionImage.objects.all().delete()
    CardVersion.objects.all().delete()
    Card.objects.all().delete()
    Template.objects.filter(key__in=["mtg-like-v1", "sorcery-v1"]).delete()

    Template.objects.create(key="mtg-like-v1", label="MTG", definition_json="{}")
    Template.objects.create(key="sorcery-v1", label="Sorcery", definition_json="{}")

    card_a = Card.objects.create(key="card-a", label="Card A")
    card_b = Card.objects.create(key="card-b", label="Card B")
    card_c = Card.objects.create(key="card-c", label="Card C")

    version_a = CardVersion.objects.create(
        card_id=card_a.id,
        version_number=1,
        template_id="mtg-like-v1",
        image_hash="hash-a",
        name="Card A",
        is_latest=True,
    )
    version_b = CardVersion.objects.create(
        card_id=card_b.id,
        version_number=1,
        template_id="mtg-like-v1",
        image_hash="hash-b",
        name="Card B",
        is_latest=True,
    )
    version_c = CardVersion.objects.create(
        card_id=card_c.id,
        version_number=1,
        template_id="sorcery-v1",
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
        source_file=str(image_a),
        stored_path=str(image_a),
        checksum="hash-a",
    )
    CardVersionImage.objects.create(
        card_version_id=version_b.id,
        source_file=str(image_b),
        stored_path=str(image_b),
        checksum="hash-b",
    )
    CardVersionImage.objects.create(
        card_version_id=version_c.id,
        source_file=str(image_c),
        stored_path=str(image_c),
        checksum="hash-c",
    )

    result = MaintenanceService().queue_reparse_latest_versions()

    jobs = list(ImportJob.objects.order_by("template_id"))
    items = list(ImportJobItem.objects.order_by("source_file"))

    assert "Queued 2 reparse jobs for 3 latest card images." == result.message
    assert result.removed_paths == []
    assert len(jobs) == 2
    assert {job.template_id for job in jobs} == {"mtg-like-v1", "sorcery-v1"}
    assert all(job.total_items >= 1 for job in jobs)
    assert {item.source_file for item in items} == {str(image_a), str(image_b), str(image_c)}

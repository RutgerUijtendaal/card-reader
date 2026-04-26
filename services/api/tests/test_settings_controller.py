from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile

from card_reader_api.catalog.views import _store_symbol_asset
from card_reader_api.maintenance import services as maintenance_services
from card_reader_api.maintenance.services import MaintenanceService
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

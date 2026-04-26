from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile

from card_reader_api.catalog.views import _store_symbol_asset
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

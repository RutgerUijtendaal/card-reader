from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from pytest import MonkeyPatch

from card_reader_api.controllers.settings_controller import upload_symbol_asset
from card_reader_core.settings import settings


def test_upload_symbol_asset_stores_under_uploads(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    upload = UploadFile(filename="Fire Mana.PNG", file=BytesIO(b"symbol-asset"))

    response = asyncio.run(upload_symbol_asset(upload))

    assert response.relative_path.startswith("uploads/fire-mana-")
    assert response.relative_path.endswith(".png")
    assert not response.relative_path.startswith("symbols/")

    stored_path = Path(response.absolute_path)
    assert stored_path.parent == tmp_path / "symbols" / "uploads"
    assert stored_path.read_bytes() == b"symbol-asset"

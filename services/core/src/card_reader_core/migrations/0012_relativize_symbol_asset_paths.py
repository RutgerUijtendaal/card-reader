from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from django.db import migrations


def _looks_absolute_path(value: str) -> bool:
    if not value:
        return False
    if value.startswith(("/", "\\")):
        return True
    return len(value) >= 3 and value[1] == ":" and value[2] in {"\\", "/"}


def _normalize_relative_storage_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part and part != "."]
    return PurePosixPath(*parts).as_posix()


def _relativize_symbol_asset_path(value: str) -> str:
    if not _looks_absolute_path(value):
        normalized = _normalize_relative_storage_path(value)
        if normalized.startswith("symbols/"):
            return normalized[len("symbols/") :]
        return normalized

    try:
        from card_reader_core.settings import settings

        relative_path = Path(value).relative_to(settings.storage_root_dir).as_posix()
        if relative_path.startswith("symbols/"):
            return relative_path[len("symbols/") :]
        return relative_path
    except Exception:
        pass

    normalized = value.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part and part != "."]
    indexes = [index for index, part in enumerate(parts) if part.lower() == "symbols"]
    if indexes:
        tail = PurePosixPath(*parts[indexes[-1] + 1 :]).as_posix()
        return tail
    return _normalize_relative_storage_path(value)


def forwards(apps: Any, schema_editor: Any) -> None:
    Symbol = apps.get_model("card_reader_core", "Symbol")
    for symbol in Symbol.objects.only("id", "reference_assets_json").iterator():
        try:
            assets = json.loads(symbol.reference_assets_json or "[]")
        except json.JSONDecodeError:
            continue
        if not isinstance(assets, list):
            continue
        normalized_assets = [
            _relativize_symbol_asset_path(asset)
            for asset in assets
            if isinstance(asset, str) and asset.strip()
        ]
        normalized_json = json.dumps(normalized_assets)
        if normalized_json == symbol.reference_assets_json:
            continue
        Symbol.objects.filter(id=symbol.id).update(reference_assets_json=normalized_json)


def backwards(apps: Any, schema_editor: Any) -> None:
    return None


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0011_relativize_import_job_paths")]

    operations = [migrations.RunPython(forwards, backwards)]

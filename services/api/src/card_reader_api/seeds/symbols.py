from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from card_reader_core.models import Symbol, now_utc
from card_reader_core.repositories import normalize_slug_key
from card_reader_core.settings import settings
from .shared import resolve_seed_file

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS_FILE = resolve_seed_file("symbols.json")
DEFAULT_SYMBOLS_ASSET_DIR = resolve_seed_file("assets/symbols")


@dataclass(slots=True)
class SymbolSeedEntry:
    key: str
    label: str
    symbol_type: str
    text_token: str
    detector_type: str
    detection_config_json: str
    enabled: bool
    asset_files: list[str]


def read_symbol_entries(seed_file: Path = DEFAULT_SYMBOLS_FILE) -> list[SymbolSeedEntry]:
    if not seed_file.exists():
        logger.warning("Symbol seed file not found; skipping. file=%s", seed_file)
        return []

    try:
        payload = json.loads(seed_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.exception("Invalid symbol seed json. file=%s", seed_file)
        return []

    if not isinstance(payload, list):
        logger.warning("Symbol seed json must be an array. file=%s", seed_file)
        return []

    out: list[SymbolSeedEntry] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        if not label:
            continue
        key = normalize_slug_key(str(item.get("key", "")).strip() or label)
        symbol_type = normalize_slug_key(str(item.get("symbol_type", "generic")).strip() or "generic")
        detector_type = str(item.get("detector_type", "template")).strip().lower() or "template"
        text_token = str(item.get("text_token", "")).strip()
        detection_config_json = str(item.get("detection_config_json", "{}")).strip() or "{}"
        enabled = bool(item.get("enabled", True))
        raw_assets = item.get("asset_files", [])
        asset_files = [
            str(value).strip()
            for value in (raw_assets if isinstance(raw_assets, list) else [])
            if str(value).strip()
        ]
        if not key:
            continue
        out.append(
            SymbolSeedEntry(
                key=key,
                label=label,
                symbol_type=symbol_type,
                text_token=text_token,
                detector_type=detector_type,
                detection_config_json=detection_config_json,
                enabled=enabled,
                asset_files=asset_files,
            )
        )
    return out


def seed_symbols(_session: Any) -> tuple[int, int]:
    entries = read_symbol_entries()
    if not entries:
        return 0, 0

    created = 0
    updated = 0
    existing_by_key = {row.key: row for row in Symbol.objects.filter(key__in=[entry.key for entry in entries])}

    for entry in entries:
        reference_assets_json = _copy_assets_and_build_references(entry.asset_files)
        existing = existing_by_key.get(entry.key)
        if existing is None:
            Symbol.objects.create(
                key=entry.key,
                label=entry.label,
                symbol_type=entry.symbol_type,
                detector_type=entry.detector_type,
                detection_config_json=entry.detection_config_json,
                reference_assets_json=reference_assets_json,
                text_token=entry.text_token,
                enabled=entry.enabled,
            )
            created += 1
            continue

        changed = False
        changed |= _set_if_diff(existing, "label", entry.label)
        changed |= _set_if_diff(existing, "symbol_type", entry.symbol_type)
        changed |= _set_if_diff(existing, "detector_type", entry.detector_type)
        changed |= _set_if_diff(existing, "detection_config_json", entry.detection_config_json)
        changed |= _set_if_diff(existing, "reference_assets_json", reference_assets_json)
        changed |= _set_if_diff(existing, "text_token", entry.text_token)
        changed |= _set_if_diff(existing, "enabled", entry.enabled)
        if changed:
            existing.updated_at = now_utc()
            existing.save()
            updated += 1

    return created, updated


def symbol_table_has_rows(_session: Any) -> bool:
    return Symbol.objects.exists()


def _copy_assets_and_build_references(asset_files: list[str]) -> str:
    references: list[str] = []
    if not asset_files:
        return "[]"

    destination_root = settings.storage_root_dir / "symbols" / "defaults"
    destination_root.mkdir(parents=True, exist_ok=True)

    for asset_name in asset_files:
        source = DEFAULT_SYMBOLS_ASSET_DIR / asset_name
        if not source.exists():
            logger.warning("Default symbol asset missing. source=%s", source)
            continue
        target = destination_root / source.name
        if not target.exists():
            shutil.copy2(source, target)
        references.append(f"defaults/{source.name}")

    return json.dumps(references)


def _set_if_diff(instance: Symbol, field_name: str, value: object) -> bool:
    if getattr(instance, field_name) == value:
        return False
    setattr(instance, field_name, value)
    return True

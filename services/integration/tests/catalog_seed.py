from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from card_reader_core.repositories.helpers import normalize_slug_key

from runtime import REPO_ROOT

if TYPE_CHECKING:
    from card_reader_core.models import Keyword, Tag, Type

CATALOG_ROOT = Path(__file__).resolve().parent / "fixtures" / "catalog"
CATALOG_FILES = {
    "keywords": CATALOG_ROOT / "seed-keywords.json",
    "tags": CATALOG_ROOT / "seed-tags.json",
    "types": CATALOG_ROOT / "seed-types.json",
    "symbols": CATALOG_ROOT / "seed-symbols.json",
    "templates": CATALOG_ROOT / "seed-templates.json",
}
CATALOG_SYMBOL_ASSETS_DIR = CATALOG_ROOT / "assets" / "symbols"


def seed_integration_catalog(*, omit_tag_keys: set[str] | None = None) -> None:
    from card_reader_core.models import Keyword, Tag, Type

    _seed_simple_rows(Keyword, CATALOG_FILES["keywords"])
    _seed_simple_rows(Tag, _build_filtered_tags_file(omit_tag_keys))
    _seed_symbols(CATALOG_FILES["symbols"], assets_dir=CATALOG_SYMBOL_ASSETS_DIR)
    _seed_templates(CATALOG_FILES["templates"])
    _seed_simple_rows(Type, CATALOG_FILES["types"])


def load_catalog_bundle(*, omit_tag_keys: set[str] | None = None) -> dict[str, Any]:
    keywords = _load_json(CATALOG_FILES["keywords"])
    tags = _load_json(_build_filtered_tags_file(omit_tag_keys))
    types = _load_json(CATALOG_FILES["types"])
    symbols = _load_json(CATALOG_FILES["symbols"])
    templates = _load_json(CATALOG_FILES["templates"])
    return {
        "keyword_keys": {_slugify_label(label) for label in keywords},
        "tag_keys": {_slugify_label(label) for label in tags},
        "type_keys": {_slugify_label(label) for label in types},
        "symbol_keys": {str(row["key"]) for row in symbols},
        "template_keys": {str(row["key"]) for row in templates},
        "symbol_assets": {
            asset_name
            for row in symbols
            for asset_name in row.get("asset_files", [])
            if isinstance(asset_name, str) and asset_name
        },
    }


def build_catalog_preflight() -> list[str]:
    issues: list[str] = []
    bundle = load_catalog_bundle()
    for asset_name in sorted(bundle["symbol_assets"]):
        asset_path = CATALOG_SYMBOL_ASSETS_DIR / asset_name
        if not asset_path.exists():
            issues.append(f"Missing catalog symbol asset: {asset_path}")
            continue
        try:
            asset_path.read_bytes()
        except OSError as exc:
            issues.append(f"Unreadable catalog symbol asset: {asset_path} ({exc})")
    issues.extend(_check_ocr_runtime())
    return issues


def _check_ocr_runtime() -> list[str]:
    from PIL import Image

    from card_reader_parser.parsers.ocr_runner import OcrRunner
    from card_reader_parser.parsers.region_config import build_ocr_engine_config

    issues: list[str] = []
    runner = OcrRunner()
    engine = runner._get_ocr_engine(build_ocr_engine_config(None))
    if engine is None:
        issues.append("Failed to initialize PaddleOCR for integration tests.")
        return issues

    probe = runner.run(Image.new("RGB", (32, 32), "white"))
    if not isinstance(probe, dict):
        issues.append("OCR probe returned an invalid payload.")
    return issues


def _seed_simple_rows(model: type[Keyword] | type[Tag] | type[Type], seed_file: Path) -> None:
    from card_reader_core.models import now_utc

    entries = _normalize_simple_entries(_read_label_entries(seed_file))
    existing_by_key = {row.key: row for row in model.objects.filter(key__in=[key for key, _, _ in entries])}
    for key, label, identifiers_json in entries:
        existing = existing_by_key.get(key)
        if existing is None:
            model.objects.create(key=key, label=label, identifiers_json=identifiers_json)
            continue
        if existing.label != label or existing.identifiers_json != identifiers_json:
            existing.label = label
            existing.identifiers_json = identifiers_json
            existing.updated_at = now_utc()
            existing.save(update_fields=["label", "identifiers_json", "updated_at"])


def _seed_templates(seed_file: Path) -> None:
    from card_reader_core.models import Template, now_utc

    rows = _load_json(seed_file)
    assert isinstance(rows, list), f"Template seed json must be an array. file={seed_file}"
    existing_by_key = {row.key: row for row in Template.objects.all()}
    for item in rows:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        key = normalize_slug_key(str(item.get("key", "")).strip() or label)
        definition = item.get("definition")
        if not label or not key or not isinstance(definition, dict):
            continue
        existing = existing_by_key.get(key)
        if existing is None:
            Template.objects.create(key=key, label=label, definition_json=definition)
            continue
        if existing.label != label or existing.definition_json != definition:
            existing.label = label
            existing.definition_json = definition
            existing.updated_at = now_utc()
            existing.save(update_fields=["label", "definition_json", "updated_at"])


def _seed_symbols(seed_file: Path, *, assets_dir: Path) -> None:
    from card_reader_core.models import Symbol, now_utc

    rows = _load_json(seed_file)
    assert isinstance(rows, list), f"Symbol seed json must be an array. file={seed_file}"
    existing_by_key = {row.key: row for row in Symbol.objects.all()}
    for item in rows:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        key = normalize_slug_key(str(item.get("key", "")).strip() or label)
        if not label or not key:
            continue
        symbol_type = normalize_slug_key(str(item.get("symbol_type", "generic")).strip() or "generic")
        detector_type = str(item.get("detector_type", "template")).strip().lower() or "template"
        detection_config_json = _parse_json_object(item.get("detection_config_json", {}))
        text_enrichment_json = _parse_json_object(item.get("text_enrichment_json", {}))
        text_token = str(item.get("text_token", "")).strip()
        enabled = bool(item.get("enabled", True))
        raw_assets = item.get("asset_files", [])
        asset_files = [
            str(value).strip()
            for value in (raw_assets if isinstance(raw_assets, list) else [])
            if isinstance(value, str) and value.strip()
        ]
        reference_assets_json = _copy_assets_and_build_references(asset_files, assets_dir=assets_dir)
        existing = existing_by_key.get(key)
        if existing is None:
            Symbol.objects.create(
                key=key,
                label=label,
                symbol_type=symbol_type,
                detector_type=detector_type,
                detection_config_json=detection_config_json,
                text_enrichment_json=text_enrichment_json,
                reference_assets_json=reference_assets_json,
                text_token=text_token,
                enabled=enabled,
            )
            continue
        changed = False
        changed |= _set_if_diff(existing, "label", label)
        changed |= _set_if_diff(existing, "symbol_type", symbol_type)
        changed |= _set_if_diff(existing, "detector_type", detector_type)
        changed |= _set_if_diff(existing, "detection_config_json", detection_config_json)
        changed |= _set_if_diff(existing, "text_enrichment_json", text_enrichment_json)
        changed |= _set_if_diff(existing, "reference_assets_json", reference_assets_json)
        changed |= _set_if_diff(existing, "text_token", text_token)
        changed |= _set_if_diff(existing, "enabled", enabled)
        if changed:
            existing.updated_at = now_utc()
            existing.save()


def _copy_assets_and_build_references(asset_files: list[str], *, assets_dir: Path) -> list[str]:
    from card_reader_core.storage import resolve_storage_path

    references: list[str] = []
    if not asset_files:
        return references
    destination_root = resolve_storage_path("symbols/defaults")
    destination_root.mkdir(parents=True, exist_ok=True)
    for asset_name in asset_files:
        source = assets_dir / asset_name
        if not source.exists():
            continue
        target = destination_root / source.name
        if not target.exists():
            shutil.copy2(source, target)
        references.append(f"defaults/{source.name}")
    return references


def _set_if_diff(instance: object, field_name: str, value: object) -> bool:
    if getattr(instance, field_name) == value:
        return False
    setattr(instance, field_name, value)
    return True


def _read_label_entries(seed_file: Path) -> list[dict[str, object]]:
    payload = _load_json(seed_file)
    assert isinstance(payload, list), f"Simple seed json must be an array. file={seed_file}"
    out: list[dict[str, object]] = []
    for item in payload:
        if isinstance(item, str):
            label = item.strip()
            if label:
                out.append({"label": label, "identifiers": []})
            continue
        if not isinstance(item, dict):
            continue
        raw_label = item.get("label")
        if not isinstance(raw_label, str) or not raw_label.strip():
            continue
        raw_identifiers = item.get("identifiers", item.get("aliases", []))
        if not isinstance(raw_identifiers, list):
            raw_identifiers = []
        identifiers = [
            identifier.strip()
            for identifier in raw_identifiers
            if isinstance(identifier, str) and identifier.strip()
        ]
        out.append({"label": raw_label.strip(), "identifiers": identifiers})
    return out


def _normalize_simple_entries(entries: list[dict[str, object]]) -> list[tuple[str, str, list[str]]]:
    out: list[tuple[str, str, list[str]]] = []
    seen: set[str] = set()
    for entry in entries:
        label = str(entry["label"])
        key = normalize_slug_key(label)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((key, label, _normalize_identifiers(label, entry.get("identifiers"))))
    return out


def _normalize_identifiers(label: str, raw_identifiers: object) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    canonical_identifier = " ".join(label.split()).strip().lower()
    if canonical_identifier:
        seen.add(canonical_identifier)
        out.append(canonical_identifier)
    if not isinstance(raw_identifiers, list):
        return out
    for raw_identifier in raw_identifiers:
        if not isinstance(raw_identifier, str):
            continue
        identifier = " ".join(raw_identifier.split()).strip().lower()
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        out.append(identifier)
    return out


def _build_filtered_tags_file(omit_tag_keys: set[str] | None) -> Path:
    if not omit_tag_keys:
        return CATALOG_FILES["tags"]
    filtered_entries = [
        label
        for label in _load_json(CATALOG_FILES["tags"])
        if _slugify_label(label) not in omit_tag_keys
    ]
    filtered_path = REPO_ROOT / "services" / "integration" / ".runtime" / "seed-tags.filtered.json"
    filtered_path.write_text(f"{json.dumps(filtered_entries, indent=2)}\n", encoding="utf-8")
    return filtered_path


def _parse_json_object(raw: object) -> dict[str, object]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(decoded, dict):
            return decoded
    return {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify_label(label: object) -> str:
    return normalize_slug_key(str(label))

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from card_reader_core.models import Keyword, now_utc
from card_reader_core.repositories.helpers import normalize_slug_key
from .shared import resolve_seed_file

DEFAULT_KEYWORDS_FILE = resolve_seed_file("seed-keywords.json")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed keyword records")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_KEYWORDS_FILE,
        help="Path to a keyword JSON file (array of labels or keyword objects)",
    )
    return parser.parse_args()


def read_keyword_entries(file_path: Path) -> list[dict[str, object]]:
    if not file_path.exists():
        logger.warning("Keyword seed file not found; skipping default keyword seed. file=%s", file_path)
        return []
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.exception("Keyword seed file is invalid JSON. file=%s", file_path)
        return []
    if not isinstance(payload, list):
        logger.warning("Keyword seed json must be an array. file=%s", file_path)
        return []
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


def normalize_entries(entries: list[dict[str, object]]) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        label = str(entry["label"])
        key = normalize_slug_key(label)
        if not key or key in seen:
            continue
        seen.add(key)
        identifiers = _normalize_identifiers(label, entry.get("identifiers"))
        out.append((key, label, json.dumps(identifiers)))
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


def seed_keywords(seed_file: Path = DEFAULT_KEYWORDS_FILE) -> tuple[int, int]:
    entries = normalize_entries(read_keyword_entries(seed_file))
    if not entries:
        return 0, 0
    existing_by_key = {row.key: row for row in Keyword.objects.filter(key__in=[key for key, _, _ in entries])}
    created = 0
    updated = 0
    for key, label, identifiers_json in entries:
        existing = existing_by_key.get(key)
        if existing is None:
            Keyword.objects.create(key=key, label=label, identifiers_json=identifiers_json)
            created += 1
            continue
        if existing.label != label or existing.identifiers_json != identifiers_json:
            existing.label = label
            existing.identifiers_json = identifiers_json
            existing.updated_at = now_utc()
            existing.save(update_fields=["label", "identifiers_json", "updated_at"])
            updated += 1
    return created, updated


def keyword_table_has_rows() -> bool:
    return Keyword.objects.exists()


def main() -> None:
    from card_reader_core.database.connection import initialize_database

    args = parse_args()
    initialize_database()
    created, updated = seed_keywords(args.file)
    print(f"Keyword seed complete. file={args.file} created={created} updated={updated}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from card_reader_core.models import Keyword, now_utc
from card_reader_core.repositories import normalize_slug_key
from .shared import resolve_seed_file

DEFAULT_KEYWORDS_FILE = resolve_seed_file("seed-keywords.json")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed keyword records")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_KEYWORDS_FILE,
        help="Path to a keyword JSON file (array of labels)",
    )
    return parser.parse_args()


def read_keyword_labels(file_path: Path) -> list[str]:
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
    return [item.strip() for item in payload if isinstance(item, str) and item.strip()]


def normalize_labels(labels: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label in labels:
        key = normalize_slug_key(label)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((key, label))
    return out


def seed_keywords(_session: Any, seed_file: Path = DEFAULT_KEYWORDS_FILE) -> tuple[int, int]:
    entries = normalize_labels(read_keyword_labels(seed_file))
    if not entries:
        return 0, 0
    existing_by_key = {row.key: row for row in Keyword.objects.filter(key__in=[key for key, _ in entries])}
    created = 0
    updated = 0
    for key, label in entries:
        existing = existing_by_key.get(key)
        if existing is None:
            Keyword.objects.create(key=key, label=label)
            created += 1
            continue
        if existing.label != label:
            existing.label = label
            existing.updated_at = now_utc()
            existing.save(update_fields=["label", "updated_at"])
            updated += 1
    return created, updated


def keyword_table_has_rows(_session: Any) -> bool:
    return Keyword.objects.exists()


def main() -> None:
    from card_reader_core.database.connection import get_session, initialize_database

    args = parse_args()
    initialize_database()
    with get_session() as session:
        created, updated = seed_keywords(session, args.file)
    print(f"Keyword seed complete. file={args.file} created={created} updated={updated}")


if __name__ == "__main__":
    main()

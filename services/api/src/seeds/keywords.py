from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sqlmodel import select

from database.connection import get_session, initialize_database
from models import Keyword, now_utc
from repositories import normalize_slug_key

DEFAULT_KEYWORDS_FILE = (
    Path(__file__).resolve().parents[3] / "core" / "seeds" / "keywords.txt"
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed keyword records")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_KEYWORDS_FILE,
        help="Path to a newline-delimited keyword file",
    )
    return parser.parse_args()


def read_keyword_labels(file_path: Path) -> list[str]:
    if not file_path.exists():
        raise FileNotFoundError(f"Keyword seed file does not exist: {file_path}")

    labels: list[str] = []
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        labels.append(line)
    return labels


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


def seed_keywords(seed_file: Path) -> tuple[int, int]:
    initialize_database()
    entries = normalize_labels(read_keyword_labels(seed_file))
    if not entries:
        return 0, 0

    keys = {key for key, _ in entries}
    created = 0
    updated = 0

    with get_session() as session:
        existing_rows = session.exec(select(Keyword).where(Keyword.key.in_(keys)))
        existing_by_key = {row.key: row for row in existing_rows}

        for key, label in entries:
            existing = existing_by_key.get(key)
            if existing is None:
                session.add(Keyword(key=key, label=label))
                created += 1
                continue

            if existing.label != label:
                existing.label = label
                existing.updated_at = now_utc()
                session.add(existing)
                updated += 1

        session.commit()

    return created, updated


def ensure_default_keywords_seeded() -> tuple[bool, int, int]:
    initialize_database()
    with get_session() as session:
        has_keywords = session.exec(select(Keyword.id).limit(1)).first() is not None
    if has_keywords:
        return False, 0, 0

    created, updated = seed_keywords(DEFAULT_KEYWORDS_FILE)
    logger.info(
        "Seeded default keywords on first boot. file=%s created=%s updated=%s",
        DEFAULT_KEYWORDS_FILE,
        created,
        updated,
    )
    return True, created, updated


def main() -> None:
    args = parse_args()
    created, updated = seed_keywords(args.file)
    print(
        f"Keyword seed complete. file={args.file} created={created} updated={updated}"
    )


if __name__ == "__main__":
    main()

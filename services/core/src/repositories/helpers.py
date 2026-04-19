from __future__ import annotations

import re


def normalize_slug_key(value: str) -> str:
    compact = " ".join(value.strip().lower().split())
    return re.sub(r"[^a-z0-9]+", "-", compact).strip("-")


def to_int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def extract_mana_symbols(normalized_fields: dict[str, str]) -> list[str]:
    raw = normalized_fields.get("mana_symbols", "").strip()
    if not raw:
        return []
    return [part for part in raw.split() if part]



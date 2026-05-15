from __future__ import annotations

import re

_INTEGER_PATTERN = re.compile(r"\d+")
_BRACE_TOKEN_PATTERN = re.compile(r"\{([^}]+)\}")
_X_ONLY_PATTERN = re.compile(r"(^|[^a-z0-9])x([^a-z0-9]|$)", re.IGNORECASE)


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


def infer_mana_value(
    *,
    mana_cost: str | None,
    mana_symbols: object,
    mana_total: str | int | None = None,
) -> int | None:
    direct_total = _coerce_mana_total(mana_total)
    if direct_total is not None:
        return direct_total

    from_cost_text = _mana_value_from_cost_text(mana_cost)
    if from_cost_text is not None:
        return from_cost_text

    symbol_tokens = _coerce_symbol_tokens(mana_symbols)
    if symbol_tokens:
        return sum(_mana_value_from_token(token) for token in symbol_tokens)

    return None


def _coerce_mana_total(value: str | int | None) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return to_int_or_none(value)
    return None


def _coerce_symbol_tokens(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _mana_value_from_token(token: str) -> int:
    normalized = token.strip().lower()
    if not normalized:
        return 0
    if normalized == "x" or any(part == "x" for part in normalized.replace("_", "-").split("-")):
        return 0
    integer_parts = [int(raw) for raw in _INTEGER_PATTERN.findall(normalized)]
    if integer_parts:
        return sum(integer_parts)
    return 1


def _mana_value_from_cost_text(value: str | None) -> int | None:
    stripped = (value or "").strip()
    if not stripped:
        return None

    x_plus_match = re.fullmatch(r"[xX]\s*\+\s*(\d+)", stripped)
    if x_plus_match:
        return int(x_plus_match.group(1))

    direct_int = to_int_or_none(stripped)
    if direct_int is not None:
        return direct_int

    brace_tokens = [token.strip() for token in _BRACE_TOKEN_PATTERN.findall(stripped) if token.strip()]
    if brace_tokens:
        return sum(_mana_value_from_token(token) for token in brace_tokens)

    integer_parts = [int(raw) for raw in _INTEGER_PATTERN.findall(stripped)]
    base_total = sum(integer_parts)
    compact = _INTEGER_PATTERN.sub(" ", stripped)
    non_numeric_parts = [part for part in re.split(r"\s+", compact) if part]
    extra_total = sum(0 if _X_ONLY_PATTERN.search(part) else 1 for part in non_numeric_parts)
    total = base_total + extra_total
    return total if total > 0 else None



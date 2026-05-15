from __future__ import annotations

import re

from django.db import migrations, models


INTEGER_PATTERN = re.compile(r"\d+")
BRACE_TOKEN_PATTERN = re.compile(r"\{([^}]+)\}")
X_ONLY_PATTERN = re.compile(r"(^|[^a-z0-9])x([^a-z0-9]|$)", re.IGNORECASE)


def backfill_mana_value(apps, _schema_editor) -> None:
    CardVersion = apps.get_model("card_reader_core", "CardVersion")

    for version in CardVersion.objects.all().iterator():
        version.mana_value = infer_mana_value(
            mana_cost=getattr(version, "mana_cost", ""),
            mana_symbols=getattr(version, "mana_symbols_json", []),
        )
        version.save(update_fields=["mana_value"])


def infer_mana_value(*, mana_cost: str | None, mana_symbols: object) -> int | None:
    stripped = (mana_cost or "").strip()
    if stripped:
        x_plus_match = re.fullmatch(r"[xX]\s*\+\s*(\d+)", stripped)
        if x_plus_match:
            return int(x_plus_match.group(1))

        if stripped.isdigit():
            return int(stripped)

        brace_tokens = [token.strip() for token in BRACE_TOKEN_PATTERN.findall(stripped) if token.strip()]
        if brace_tokens:
            return sum(mana_value_from_token(token) for token in brace_tokens)

        integer_parts = [int(raw) for raw in INTEGER_PATTERN.findall(stripped)]
        base_total = sum(integer_parts)
        compact = INTEGER_PATTERN.sub(" ", stripped)
        non_numeric_parts = [part for part in re.split(r"\s+", compact) if part]
        extra_total = sum(0 if X_ONLY_PATTERN.search(part) else 1 for part in non_numeric_parts)
        total = base_total + extra_total
        if total > 0:
            return total

    symbol_tokens = [str(item).strip() for item in mana_symbols if str(item).strip()] if isinstance(mana_symbols, list) else []
    if symbol_tokens:
        return sum(mana_value_from_token(token) for token in symbol_tokens)

    return None


def mana_value_from_token(token: str) -> int:
    normalized = token.strip().lower()
    if not normalized:
        return 0
    if normalized == "x" or any(part == "x" for part in normalized.replace("_", "-").split("-")):
        return 0
    integer_parts = [int(raw) for raw in INTEGER_PATTERN.findall(normalized)]
    if integer_parts:
        return sum(integer_parts)
    return 1


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0015_drop_card_version_search")]

    operations = [
        migrations.AddField(
            model_name="cardversion",
            name="mana_value",
            field=models.IntegerField(db_index=True, default=None, null=True),
        ),
        migrations.RunPython(backfill_mana_value, reverse_code=migrations.RunPython.noop),
    ]

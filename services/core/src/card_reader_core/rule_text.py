from __future__ import annotations

import re
from typing import Mapping


SYMBOL_PLACEHOLDER_PATTERN = re.compile(r"\[\[symbol:([a-z0-9-]+)\]\]")


def build_symbol_placeholder(symbol_key: str) -> str:
    return f"[[symbol:{symbol_key.strip().lower()}]]"


def replace_symbol_placeholder_key(
    enriched_text: str,
    *,
    old_symbol_key: str,
    new_symbol_key: str,
) -> str:
    return enriched_text.replace(
        build_symbol_placeholder(old_symbol_key),
        build_symbol_placeholder(new_symbol_key),
    )


def render_enriched_rule_text(
    enriched_text: str,
    *,
    symbol_tokens_by_key: Mapping[str, str],
) -> str:
    def replace(match: re.Match[str]) -> str:
        symbol_key = match.group(1)
        token = symbol_tokens_by_key.get(symbol_key)
        if token is not None and token.strip():
            return token
        return symbol_key

    return SYMBOL_PLACEHOLDER_PATTERN.sub(replace, enriched_text)

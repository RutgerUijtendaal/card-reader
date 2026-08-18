from __future__ import annotations

from typing import Mapping

from card_reader_core.markup import (
    SYMBOL_PLACEHOLDER_PATTERN as SYMBOL_PLACEHOLDER_PATTERN,
    build_symbol_placeholder as build_symbol_placeholder,
    render_markup_plain,
    replace_symbol_placeholder_key as replace_symbol_placeholder_key,
)


def render_enriched_rule_text(
    enriched_text: str,
    *,
    symbol_tokens_by_key: Mapping[str, str],
) -> str:
    return render_markup_plain(
        enriched_text,
        symbol_tokens_by_key=symbol_tokens_by_key,
    )

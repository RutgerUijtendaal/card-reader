from __future__ import annotations

from card_reader_core.models import CardVersion, now_utc
from card_reader_core.rules import render_enriched_rule_text, replace_symbol_placeholder_key

from .links import get_symbols_for_card_version


def refresh_rule_text_for_symbol(
    *,
    symbol_id: str,
    old_key: str | None = None,
    new_key: str | None = None,
) -> int:
    versions = list(
        CardVersion.objects.filter(card_version_symbols__symbol_id=symbol_id)
        .distinct()
    )
    changed_versions: list[CardVersion] = []

    for version in versions:
        enriched_text = version.rules_text_enriched
        if old_key and new_key and old_key != new_key:
            enriched_text = replace_symbol_placeholder_key(
                enriched_text,
                old_symbol_key=old_key,
                new_symbol_key=new_key,
            )

        symbol_tokens_by_key = {
            symbol.key: symbol.text_token
            for symbol in get_symbols_for_card_version(version.id)
        }
        rendered_text = render_enriched_rule_text(
            enriched_text,
            symbol_tokens_by_key=symbol_tokens_by_key,
        )
        if enriched_text == version.rules_text_enriched and rendered_text == version.rules_text:
            continue

        version.rules_text_enriched = enriched_text
        version.rules_text = rendered_text
        version.updated_at = now_utc()
        changed_versions.append(version)

    if changed_versions:
        CardVersion.objects.bulk_update(
            changed_versions,
            ["rules_text_enriched", "rules_text", "updated_at"],
        )
    return len(changed_versions)

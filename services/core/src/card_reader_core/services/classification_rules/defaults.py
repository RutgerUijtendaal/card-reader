from __future__ import annotations

from collections.abc import Collection

from django.db import transaction

from card_reader_core.metadata import MANA_FAMILIES, MANA_FAMILY_BY_SYMBOL_KEY
from card_reader_core.models import (
    CARD_CLASSIFICATION_SOURCE_SYMBOL,
    CARD_CLASSIFICATION_TARGET_MANA_FAMILY,
    PLAYER_CARD_POOL,
    Symbol,
)
from card_reader_core.repositories.classification_rules import list_classification_rules
from card_reader_core.repositories.metadata import list_symbols

from .service import (
    ClassificationRuleDuplicateError,
    ClassificationRuleError,
    ClassificationRuleService,
)


def ensure_default_mana_family_classification_rules(
    *,
    symbol_keys: Collection[str] | None = None,
) -> int:
    """Create missing Player Symbol rules without overriding administrator choices."""
    canonical_symbol_keys = {
        symbol_key for family in MANA_FAMILIES for symbol_key in family.symbol_keys
    }
    selected_symbol_keys = (
        canonical_symbol_keys
        if symbol_keys is None
        else canonical_symbol_keys.intersection(symbol_keys)
    )
    if not selected_symbol_keys:
        return 0
    symbols_by_key = {
        symbol.key: symbol for symbol in list_symbols(keys=selected_symbol_keys)
    }
    existing = {
        (rule.target_key, rule.symbol.id)
        for rule in list_classification_rules(card_pool=PLAYER_CARD_POOL)
        if rule.target_kind == CARD_CLASSIFICATION_TARGET_MANA_FAMILY
        and rule.source_kind == CARD_CLASSIFICATION_SOURCE_SYMBOL
        and rule.symbol is not None
    }
    created = 0
    service = ClassificationRuleService()
    for family in MANA_FAMILIES:
        for symbol_key in family.symbol_keys:
            if symbol_key not in selected_symbol_keys:
                continue
            symbol = symbols_by_key.get(symbol_key)
            if symbol is None or (family.key, symbol.id) in existing:
                continue
            try:
                service.create_rule(
                    card_pool=PLAYER_CARD_POOL,
                    target_kind=CARD_CLASSIFICATION_TARGET_MANA_FAMILY,
                    target_key=family.key,
                    source_kind=CARD_CLASSIFICATION_SOURCE_SYMBOL,
                    source_id=symbol.id,
                    enabled=True,
                )
            except ClassificationRuleDuplicateError:
                continue
            created += 1
    return created


@transaction.atomic
def reconcile_mana_family_rules_for_symbol_rename(
    *,
    symbol: Symbol,
    previous_key: str,
) -> int:
    """Align a renamed canonical Symbol with its single represented mana family."""
    next_family = MANA_FAMILY_BY_SYMBOL_KEY.get(symbol.key)
    if next_family is None:
        return 0

    previous_family = MANA_FAMILY_BY_SYMBOL_KEY.get(previous_key)
    service = ClassificationRuleService()
    conflicting_rules = [
        rule
        for rule in service.rules_for_source(
            source_kind=CARD_CLASSIFICATION_SOURCE_SYMBOL,
            source_id=symbol.id,
        )
        if rule.card_pool == PLAYER_CARD_POOL
        and rule.target_kind == CARD_CLASSIFICATION_TARGET_MANA_FAMILY
        and rule.target_key != next_family.key
    ]
    stale_rule_ids = {
        rule.id
        for rule in conflicting_rules
        if previous_family is not None and rule.target_key == previous_family.key
    }
    unreconciled_rules = [
        rule for rule in conflicting_rules if rule.id not in stale_rule_ids
    ]
    if unreconciled_rules:
        targets = ", ".join(sorted({rule.target_key for rule in unreconciled_rules}))
        raise ClassificationRuleError(
            "Symbol has mana-family rules that conflict with its canonical key "
            f"({targets}). Remove or repoint those rules before renaming it."
        )

    for rule_id in stale_rule_ids:
        service.delete_rule(rule_id=rule_id)

    return ensure_default_mana_family_classification_rules(symbol_keys={symbol.key})

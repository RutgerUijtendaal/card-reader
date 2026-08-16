from __future__ import annotations

from card_reader_core.metadata import MANA_FAMILIES
from card_reader_core.models import (
    CARD_CLASSIFICATION_SOURCE_SYMBOL,
    CARD_CLASSIFICATION_TARGET_MANA_FAMILY,
    PLAYER_CARD_POOL,
)
from card_reader_core.repositories.classification_rules import list_classification_rules
from card_reader_core.repositories.metadata import list_symbols

from .service import ClassificationRuleDuplicateError, ClassificationRuleService


def ensure_default_mana_family_classification_rules() -> int:
    """Create missing Player Symbol rules without overriding administrator choices."""
    symbol_keys = {
        symbol_key for family in MANA_FAMILIES for symbol_key in family.symbol_keys
    }
    symbols_by_key = {symbol.key: symbol for symbol in list_symbols(keys=symbol_keys)}
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

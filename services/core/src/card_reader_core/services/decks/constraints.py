from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Self

from card_reader_core.models import Card

from .types import (
    MAX_DECK_COPIES,
    MAX_MAINBOARD_CARD_COUNT,
    MAX_SIDEBOARD_ENTRY_QUANTITY,
    MIN_MAINBOARD_CARD_COUNT,
    MIN_MAINBOARD_MANA_TYPE_COUNT,
)

DeckBoard = Literal["mainboard", "sideboard"]
DeckConstraintSeverity = Literal["hard", "soft"]
DeckConstraintScope = Literal["mainboard", "whole_deck"]

MAINBOARD_COPY_LIMIT_RULE_ID = "mainboard_copy_limit"
MAINBOARD_CARD_COUNT_RULE_ID = "mainboard_card_count"
MANA_TYPE_COUNT_RULE_ID = "mana_type_count"
LEGENDARY_COPY_LIMIT_RULE_ID = "legendary_copy_limit"
SIDEBOARD_ENTRY_QUANTITY_RULE_ID = "sideboard_entry_quantity"
LEGENDARY_TYPE_KEY = "legendary"
MANA_TYPE_KEY = "mana"

DEFAULT_DECK_BUILDING_CONFIG: dict[str, object] = {"overrides": {}}
DECK_CONSTRAINT_SEVERITIES: tuple[DeckConstraintSeverity, ...] = ("hard", "soft")
DECK_CONSTRAINT_SCOPES: tuple[DeckConstraintScope, ...] = ("mainboard", "whole_deck")
SUPPORTED_RULE_IDS = {
    MAINBOARD_COPY_LIMIT_RULE_ID,
    MAINBOARD_CARD_COUNT_RULE_ID,
    MANA_TYPE_COUNT_RULE_ID,
    LEGENDARY_COPY_LIMIT_RULE_ID,
    SIDEBOARD_ENTRY_QUANTITY_RULE_ID,
}
DECK_BUILDING_CONFIG_EXAMPLE: dict[str, object] = {
    "overrides": {
        MAINBOARD_COPY_LIMIT_RULE_ID: {
            "max": 6,
        },
        MANA_TYPE_COUNT_RULE_ID: {
            "min": 0,
        },
        LEGENDARY_COPY_LIMIT_RULE_ID: {
            "severity": "hard",
            "scope": "whole_deck",
            "blocks_action": True,
            "max": 1,
        },
    }
}


@dataclass(frozen=True)
class DeckConstraintRule:
    rule_id: str
    severity: DeckConstraintSeverity
    scope: DeckConstraintScope
    blocks_action: bool
    min_count: int | None = None
    max_count: int | None = None

    def with_override(self, raw_override: object) -> Self:
        if not isinstance(raw_override, dict):
            return self

        severity = raw_override.get("severity")
        scope = raw_override.get("scope")
        blocks_action = raw_override.get("blocks_action")
        min_count = raw_override.get("min")
        max_count = raw_override.get("max")
        if "count" in raw_override:
            min_count = raw_override["count"]
        if "minimum" in raw_override:
            min_count = raw_override["minimum"]
        if "maximum" in raw_override:
            max_count = raw_override["maximum"]

        return replace(
            self,
            severity=severity if severity in ("hard", "soft") else self.severity,
            scope=scope if scope in ("mainboard", "whole_deck") else self.scope,
            blocks_action=blocks_action if isinstance(blocks_action, bool) else self.blocks_action,
            min_count=_non_negative_int_or_current(min_count, self.min_count),
            max_count=_non_negative_int_or_current(max_count, self.max_count),
        )


@dataclass(frozen=True)
class DeckConstraintRules:
    mainboard_copy_limit: DeckConstraintRule
    mainboard_card_count: DeckConstraintRule
    mana_type_count: DeckConstraintRule
    legendary_copy_limit: DeckConstraintRule
    sideboard_entry_quantity: DeckConstraintRule

    @classmethod
    def defaults(cls) -> Self:
        return cls(
            mainboard_copy_limit=DeckConstraintRule(
                rule_id=MAINBOARD_COPY_LIMIT_RULE_ID,
                severity="hard",
                scope="mainboard",
                blocks_action=True,
                max_count=MAX_DECK_COPIES,
            ),
            mainboard_card_count=DeckConstraintRule(
                rule_id=MAINBOARD_CARD_COUNT_RULE_ID,
                severity="hard",
                scope="mainboard",
                blocks_action=True,
                min_count=MIN_MAINBOARD_CARD_COUNT,
                max_count=MAX_MAINBOARD_CARD_COUNT,
            ),
            mana_type_count=DeckConstraintRule(
                rule_id=MANA_TYPE_COUNT_RULE_ID,
                severity="hard",
                scope="mainboard",
                blocks_action=False,
                min_count=MIN_MAINBOARD_MANA_TYPE_COUNT,
            ),
            legendary_copy_limit=DeckConstraintRule(
                rule_id=LEGENDARY_COPY_LIMIT_RULE_ID,
                severity="soft",
                scope="mainboard",
                blocks_action=False,
                max_count=1,
            ),
            sideboard_entry_quantity=DeckConstraintRule(
                rule_id=SIDEBOARD_ENTRY_QUANTITY_RULE_ID,
                severity="hard",
                scope="mainboard",
                blocks_action=True,
                max_count=MAX_SIDEBOARD_ENTRY_QUANTITY,
            ),
        )

    def apply_config(self, config: object) -> Self:
        overrides = _extract_rule_overrides(config)
        return replace(
            self,
            mainboard_copy_limit=self.mainboard_copy_limit.with_override(
                overrides.get(MAINBOARD_COPY_LIMIT_RULE_ID)
            ),
            mainboard_card_count=self.mainboard_card_count.with_override(
                overrides.get(MAINBOARD_CARD_COUNT_RULE_ID)
            ),
            mana_type_count=self.mana_type_count.with_override(overrides.get(MANA_TYPE_COUNT_RULE_ID)),
            legendary_copy_limit=self.legendary_copy_limit.with_override(
                overrides.get(LEGENDARY_COPY_LIMIT_RULE_ID)
            ),
            sideboard_entry_quantity=self.sideboard_entry_quantity.with_override(
                overrides.get(SIDEBOARD_ENTRY_QUANTITY_RULE_ID)
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "mainboard_copy_limit": _rule_to_json(self.mainboard_copy_limit),
            "mainboard_card_count": _rule_to_json(self.mainboard_card_count),
            "mana_type_count": _rule_to_json(self.mana_type_count),
            "legendary_copy_limit": _rule_to_json(self.legendary_copy_limit),
            "sideboard_entry_quantity": _rule_to_json(self.sideboard_entry_quantity),
        }


@dataclass(frozen=True)
class DeckConstraintEntry:
    card: Card
    quantity: int
    board: DeckBoard


@dataclass(frozen=True)
class DeckConstraintViolation:
    rule_id: str
    severity: DeckConstraintSeverity
    scope: DeckConstraintScope
    blocks_action: bool
    message: str
    card_id: str | None = None
    board: DeckBoard | None = None


@dataclass(frozen=True)
class DeckConstraintEvaluation:
    rules: DeckConstraintRules
    violations: list[DeckConstraintViolation]

    @property
    def hard_violations(self) -> list[DeckConstraintViolation]:
        return [violation for violation in self.violations if violation.severity == "hard"]

    @property
    def soft_violations(self) -> list[DeckConstraintViolation]:
        return [violation for violation in self.violations if violation.severity == "soft"]

    @property
    def blocking_violations(self) -> list[DeckConstraintViolation]:
        return [
            violation
            for violation in self.hard_violations
            if violation.blocks_action
        ]


class DeckConstraintEvaluator:
    def evaluate(
        self,
        *,
        hero_card: Card | None,
        entries: list[DeckConstraintEntry],
    ) -> DeckConstraintEvaluation:
        rules = self.resolve_rules(hero_card=hero_card, entries=entries)
        return DeckConstraintEvaluation(
            rules=rules,
            violations=[
                *self._validate_mainboard_copy_limits(entries, rules.mainboard_copy_limit),
                *self._validate_sideboard_entry_quantities(entries, rules.sideboard_entry_quantity),
                *self._validate_legendary_copy_limits(entries, rules.legendary_copy_limit),
                *self._validate_mainboard_card_count(entries, rules.mainboard_card_count),
                *self._validate_mana_type_count(entries, rules.mana_type_count),
            ],
        )

    def validate_entries(
        self,
        entries: list[DeckConstraintEntry],
        *,
        hero_card: Card | None = None,
    ) -> list[DeckConstraintViolation]:
        return self.evaluate(hero_card=hero_card, entries=entries).violations

    def resolve_rules(
        self,
        *,
        hero_card: Card | None,
        entries: list[DeckConstraintEntry],
    ) -> DeckConstraintRules:
        rules = DeckConstraintRules.defaults()
        if hero_card is not None:
            rules = rules.apply_config(hero_card.deck_building_config_json)
        for entry in entries:
            rules = rules.apply_config(entry.card.deck_building_config_json)
        return rules

    def _validate_mainboard_copy_limits(
        self,
        entries: list[DeckConstraintEntry],
        rule: DeckConstraintRule,
    ) -> list[DeckConstraintViolation]:
        if rule.max_count is None:
            return []
        scoped_entries = _scoped_entries(entries, rule.scope)
        if rule.scope == "whole_deck":
            totals_by_card_id: dict[str, int] = {}
            cards_by_id: dict[str, Card] = {}
            invalid_entry_cards: set[str] = set()
            for entry in scoped_entries:
                card_id = entry.card.id
                totals_by_card_id[card_id] = totals_by_card_id.get(card_id, 0) + entry.quantity
                cards_by_id[card_id] = entry.card
                if entry.quantity < 1:
                    invalid_entry_cards.add(card_id)
            invalid_card_ids = {
                card_id
                for card_id, quantity in totals_by_card_id.items()
                if quantity > rule.max_count
            } | invalid_entry_cards
            return [
                DeckConstraintViolation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    scope=rule.scope,
                    blocks_action=rule.blocks_action,
                    card_id=card_id,
                    message=f"Each mainboard card quantity must be between 1 and {rule.max_count}.",
                )
                for card_id in sorted(invalid_card_ids)
                if card_id in cards_by_id
            ]
        return [
            DeckConstraintViolation(
                rule_id=rule.rule_id,
                severity=rule.severity,
                scope=rule.scope,
                blocks_action=rule.blocks_action,
                card_id=entry.card.id,
                board=entry.board,
                message=f"Each mainboard card quantity must be between 1 and {rule.max_count}.",
            )
            for entry in entries
            if entry.board == "mainboard" and (entry.quantity < 1 or entry.quantity > rule.max_count)
        ]

    def _validate_sideboard_entry_quantities(
        self,
        entries: list[DeckConstraintEntry],
        rule: DeckConstraintRule,
    ) -> list[DeckConstraintViolation]:
        if rule.max_count is None:
            return []
        return [
            DeckConstraintViolation(
                rule_id=rule.rule_id,
                severity=rule.severity,
                scope=rule.scope,
                blocks_action=rule.blocks_action,
                card_id=entry.card.id,
                board=entry.board,
                message=f"Each sideboard card quantity must be between 1 and {rule.max_count}.",
            )
            for entry in entries
            if entry.board == "sideboard" and (entry.quantity < 1 or entry.quantity > rule.max_count)
        ]

    def _validate_legendary_copy_limits(
        self,
        entries: list[DeckConstraintEntry],
        rule: DeckConstraintRule,
    ) -> list[DeckConstraintViolation]:
        if rule.max_count is None:
            return []

        scoped_entries = _scoped_entries(entries, rule.scope)
        totals_by_card_id: dict[str, int] = {}
        legendary_cards: dict[str, Card] = {}
        for entry in scoped_entries:
            card_id = entry.card.id
            totals_by_card_id[card_id] = totals_by_card_id.get(card_id, 0) + entry.quantity
            if _card_has_type(entry.card, LEGENDARY_TYPE_KEY):
                legendary_cards[card_id] = entry.card

        return [
            DeckConstraintViolation(
                rule_id=rule.rule_id,
                severity=rule.severity,
                scope=rule.scope,
                blocks_action=rule.blocks_action,
                card_id=card_id,
                message=f"Legendary cards are limited to {rule.max_count} copy per deck.",
            )
            for card_id in sorted(legendary_cards)
            if totals_by_card_id.get(card_id, 0) > rule.max_count
        ]

    def _validate_mainboard_card_count(
        self,
        entries: list[DeckConstraintEntry],
        rule: DeckConstraintRule,
    ) -> list[DeckConstraintViolation]:
        total = sum(entry.quantity for entry in _scoped_entries(entries, rule.scope))
        violations: list[DeckConstraintViolation] = []
        if rule.min_count is not None and total < rule.min_count:
            violations.append(
                DeckConstraintViolation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    scope=rule.scope,
                    blocks_action=False,
                    message=f"Deck must contain at least {rule.min_count} mainboard cards.",
                )
            )
        if rule.max_count is not None and total > rule.max_count:
            violations.append(
                DeckConstraintViolation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    scope=rule.scope,
                    blocks_action=rule.blocks_action,
                    message=f"Deck cannot contain more than {rule.max_count} mainboard cards.",
                )
            )
        return violations

    def _validate_mana_type_count(
        self,
        entries: list[DeckConstraintEntry],
        rule: DeckConstraintRule,
    ) -> list[DeckConstraintViolation]:
        if rule.min_count is None:
            return []
        mana_type_cards = sum(
            entry.quantity
            for entry in _scoped_entries(entries, rule.scope)
            if _card_has_type(entry.card, MANA_TYPE_KEY)
        )
        if mana_type_cards >= rule.min_count:
            return []
        return [
            DeckConstraintViolation(
                rule_id=rule.rule_id,
                severity=rule.severity,
                scope=rule.scope,
                blocks_action=rule.blocks_action,
                message=f"Deck must contain at least {rule.min_count} mainboard cards with type 'Mana'.",
            )
        ]


def normalize_deck_building_config(value: object) -> dict[str, object]:
    if value in (None, ""):
        return dict(DEFAULT_DECK_BUILDING_CONFIG)
    if not isinstance(value, dict):
        raise ValueError("Deck-building config must be a JSON object.")
    if "overrides" in value and not isinstance(value["overrides"], dict):
        raise ValueError("Deck-building config overrides must be a JSON object.")
    overrides = _extract_rule_overrides(value)
    normalized_overrides: dict[str, object] = {}
    for rule_id, override in overrides.items():
        if rule_id not in SUPPORTED_RULE_IDS:
            raise ValueError(f"Unsupported deck-building rule id: {rule_id}.")
        if not isinstance(override, dict):
            raise ValueError("Deck-building rule overrides must be JSON objects.")
        normalized_override: dict[str, object] = {}
        for key, raw_value in override.items():
            if key in {"severity"}:
                if raw_value not in ("hard", "soft"):
                    raise ValueError("Deck-building rule severity must be 'hard' or 'soft'.")
                normalized_override[key] = raw_value
            elif key == "scope":
                if raw_value not in ("mainboard", "whole_deck"):
                    raise ValueError("Deck-building rule scope must be 'mainboard' or 'whole_deck'.")
                normalized_override[key] = raw_value
            elif key == "blocks_action":
                if not isinstance(raw_value, bool):
                    raise ValueError("Deck-building blocks_action must be a boolean.")
                normalized_override[key] = raw_value
            elif key in {"min", "max", "count", "minimum", "maximum"}:
                if isinstance(raw_value, bool) or not isinstance(raw_value, int) or raw_value < 0:
                    raise ValueError("Deck-building numeric rule values must be non-negative integers.")
                normalized_override[key] = raw_value
            else:
                raise ValueError(f"Unsupported deck-building override field: {key}.")
        normalized_overrides[rule_id] = normalized_override
    return {"overrides": normalized_overrides}


def effective_deck_building_rules_json(
    *,
    hero_card: Card | None,
    entries: list[DeckConstraintEntry],
) -> dict[str, object]:
    return DeckConstraintEvaluator().resolve_rules(hero_card=hero_card, entries=entries).to_json()


def deck_building_rules_metadata_json() -> dict[str, object]:
    return {
        "supported_rule_ids": sorted(SUPPORTED_RULE_IDS),
        "allowed_severities": list(DECK_CONSTRAINT_SEVERITIES),
        "allowed_scopes": list(DECK_CONSTRAINT_SCOPES),
        "default_config": DEFAULT_DECK_BUILDING_CONFIG,
        "default_rules": DeckConstraintRules.defaults().to_json(),
        "example_config": DECK_BUILDING_CONFIG_EXAMPLE,
    }


def _extract_rule_overrides(config: object) -> dict[str, object]:
    if not isinstance(config, dict):
        return {}
    overrides = config.get("overrides", config)
    if not isinstance(overrides, dict):
        return {}
    return {str(key): value for key, value in overrides.items()}


def _rule_to_json(rule: DeckConstraintRule) -> dict[str, object]:
    payload: dict[str, object] = {
        "rule_id": rule.rule_id,
        "severity": rule.severity,
        "scope": rule.scope,
        "blocks_action": rule.blocks_action,
    }
    if rule.min_count is not None:
        payload["min"] = rule.min_count
    if rule.max_count is not None:
        payload["max"] = rule.max_count
    return payload


def _non_negative_int_or_current(value: object, current: int | None) -> int | None:
    if isinstance(value, bool):
        return current
    if isinstance(value, int) and value >= 0:
        return value
    return current


def _scoped_entries(
    entries: list[DeckConstraintEntry],
    scope: DeckConstraintScope,
) -> list[DeckConstraintEntry]:
    if scope == "whole_deck":
        return entries
    return [entry for entry in entries if entry.board == "mainboard"]


def _card_has_type(card: Card, type_key: str) -> bool:
    version = card.latest_version
    if version is None:
        return False
    normalized_key = type_key.strip().lower()
    return any(row.type.key.strip().lower() == normalized_key for row in version.card_version_types.all())

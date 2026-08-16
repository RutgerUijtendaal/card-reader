from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import cast

from django.db import IntegrityError, transaction

from card_reader_core.models import (
    CARD_CLASSIFICATION_SOURCE_SYMBOL,
    CARD_CLASSIFICATION_SOURCE_TAG,
    CARD_CLASSIFICATION_SOURCE_TYPE,
    CARD_CLASSIFICATION_TARGET_FACTION,
    CARD_CLASSIFICATION_TARGET_MANA_FAMILY,
    CARD_CLASSIFICATION_TARGET_ROLE,
    CARD_FACTION_DEFINITIONS,
    CARD_FACTIONS,
    CARD_POOL_DEFINITIONS,
    CARD_ROLE_DEFINITIONS,
    CARD_ROLES,
    STANDARD_CARD_ROLE,
    CardClassificationRule,
    CardPool,
    CardPoolScope,
    Symbol,
    Tag,
    Type,
    is_card_pool,
)
from card_reader_core.metadata import MANA_FAMILIES, MANA_FAMILY_BY_KEY
from card_reader_core.repositories.classification_rules import (
    create_classification_rule,
    delete_classification_rule,
    get_classification_usage_counts,
    get_classification_rule,
    list_classification_rules,
    list_rules_for_source,
    update_classification_rule,
)
from card_reader_core.repositories.metadata import get_symbol, get_tag, get_type, list_symbols


CLASSIFICATION_RULE_SNAPSHOT_SCHEMA_VERSION = 3
SUPPORTED_CLASSIFICATION_RULE_SNAPSHOT_SCHEMA_VERSIONS = (1, 2, 3)


class ClassificationRuleError(ValueError):
    pass


class ClassificationRuleNotFoundError(ClassificationRuleError):
    pass


class ClassificationRuleDuplicateError(ClassificationRuleError):
    pass


class ClassificationRuleSourceNotFoundError(ClassificationRuleError):
    pass


def _target_keys(target_kind: str) -> tuple[str, ...]:
    if target_kind == CARD_CLASSIFICATION_TARGET_ROLE:
        return cast(tuple[str, ...], CARD_ROLES)
    if target_kind == CARD_CLASSIFICATION_TARGET_FACTION:
        return cast(tuple[str, ...], CARD_FACTIONS)
    if target_kind == CARD_CLASSIFICATION_TARGET_MANA_FAMILY:
        return cast(tuple[str, ...], tuple(MANA_FAMILY_BY_KEY))
    raise ClassificationRuleError("target_kind must be role, faction, or mana_family.")


def _source(
    source_kind: str, source_id: str
) -> tuple[Tag | None, Type | None, Symbol | None]:
    if source_kind == CARD_CLASSIFICATION_SOURCE_TAG:
        tag = get_tag(source_id)
        if tag is None:
            raise ClassificationRuleSourceNotFoundError("Tag source not found.")
        return tag, None, None
    if source_kind == CARD_CLASSIFICATION_SOURCE_TYPE:
        type_row = get_type(source_id)
        if type_row is None:
            raise ClassificationRuleSourceNotFoundError("Type source not found.")
        return None, type_row, None
    if source_kind == CARD_CLASSIFICATION_SOURCE_SYMBOL:
        symbol = get_symbol(source_id)
        if symbol is None:
            raise ClassificationRuleSourceNotFoundError("Symbol source not found.")
        return None, None, symbol
    raise ClassificationRuleError("source_kind must be tag, type, or symbol.")


def _rule_source(rule: CardClassificationRule) -> Tag | Type | Symbol | None:
    if rule.source_kind == CARD_CLASSIFICATION_SOURCE_TAG:
        return rule.tag
    if rule.source_kind == CARD_CLASSIFICATION_SOURCE_TYPE:
        return rule.type
    if rule.source_kind == CARD_CLASSIFICATION_SOURCE_SYMBOL:
        return rule.symbol
    return None


def _validate_identity(*, card_pool: str, target_kind: str, target_key: str) -> CardPool:
    if not is_card_pool(card_pool):
        raise ClassificationRuleError(f"Unsupported card pool: {card_pool}")
    if target_key not in _target_keys(target_kind):
        raise ClassificationRuleError(f"Unsupported {target_kind} target key: {target_key}")
    return card_pool


def classification_rule_payload(rule: CardClassificationRule) -> dict[str, object]:
    source = _rule_source(rule)
    if source is None:
        raise ClassificationRuleError(f"Rule {rule.id} has an invalid source reference.")
    return {
        "id": rule.id,
        "card_pool": rule.card_pool,
        "target_kind": rule.target_kind,
        "target_key": rule.target_key,
        "source_kind": rule.source_kind,
        "source_id": source.id,
        "source_key": source.key,
        "source_label": source.label,
        "enabled": rule.enabled,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


class ClassificationRuleService:
    def list_rules(self) -> list[CardClassificationRule]:
        return list_classification_rules()

    def get_rule(self, rule_id: str) -> CardClassificationRule | None:
        return get_classification_rule(rule_id)

    @transaction.atomic
    def create_rule(
        self,
        *,
        card_pool: str,
        target_kind: str,
        target_key: str,
        source_kind: str,
        source_id: str,
        enabled: bool = True,
    ) -> CardClassificationRule:
        normalized_pool = _validate_identity(
            card_pool=card_pool,
            target_kind=target_kind,
            target_key=target_key,
        )
        tag, type_row, symbol = _source(source_kind, source_id)
        try:
            return create_classification_rule(
                card_pool=normalized_pool,
                target_kind=target_kind,
                target_key=target_key,
                source_kind=source_kind,
                tag=tag,
                type=type_row,
                symbol=symbol,
                enabled=enabled,
            )
        except IntegrityError as exc:
            raise ClassificationRuleDuplicateError(
                "This pool, target, and source rule already exists."
            ) from exc

    @transaction.atomic
    def update_rule(
        self,
        *,
        rule_id: str,
        card_pool: str | None = None,
        target_kind: str | None = None,
        target_key: str | None = None,
        source_kind: str | None = None,
        source_id: str | None = None,
        enabled: bool | None = None,
    ) -> CardClassificationRule:
        rule = get_classification_rule(rule_id)
        if rule is None:
            raise ClassificationRuleNotFoundError("Classification rule not found.")
        next_pool = card_pool if card_pool is not None else rule.card_pool
        next_target_kind = target_kind if target_kind is not None else rule.target_kind
        next_target_key = target_key if target_key is not None else rule.target_key
        _validate_identity(
            card_pool=next_pool,
            target_kind=next_target_kind,
            target_key=next_target_key,
        )
        next_source_kind = source_kind if source_kind is not None else rule.source_kind
        current_source = _rule_source(rule)
        next_source_id = (
            source_id if source_id is not None else (current_source.id if current_source else "")
        )
        tag, type_row, symbol = _source(next_source_kind, next_source_id)
        updates: dict[str, object] = {
            "card_pool": next_pool,
            "target_kind": next_target_kind,
            "target_key": next_target_key,
            "source_kind": next_source_kind,
            "tag": tag,
            "type": type_row,
            "symbol": symbol,
        }
        if enabled is not None:
            updates["enabled"] = enabled
        try:
            return update_classification_rule(rule, updates=updates)
        except IntegrityError as exc:
            raise ClassificationRuleDuplicateError(
                "This pool, target, and source rule already exists."
            ) from exc

    @transaction.atomic
    def delete_rule(self, *, rule_id: str) -> None:
        rule = get_classification_rule(rule_id)
        if rule is None:
            raise ClassificationRuleNotFoundError("Classification rule not found.")
        delete_classification_rule(rule)

    def rules_for_source(self, *, source_kind: str, source_id: str) -> list[CardClassificationRule]:
        if source_kind not in {
            CARD_CLASSIFICATION_SOURCE_TAG,
            CARD_CLASSIFICATION_SOURCE_TYPE,
            CARD_CLASSIFICATION_SOURCE_SYMBOL,
        }:
            raise ClassificationRuleError("source_kind must be tag, type, or symbol.")
        return list_rules_for_source(source_kind=source_kind, source_id=source_id)

    def build_snapshot(
        self,
        *,
        card_pool: CardPool,
        include_roles: bool,
        include_factions: bool,
        include_mana_families: bool = False,
    ) -> dict[str, object]:
        target_kinds: list[str] = []
        if include_roles:
            target_kinds.append(CARD_CLASSIFICATION_TARGET_ROLE)
        if include_factions:
            target_kinds.append(CARD_CLASSIFICATION_TARGET_FACTION)
        if include_mana_families:
            target_kinds.append(CARD_CLASSIFICATION_TARGET_MANA_FAMILY)
        rules = (
            list_classification_rules(
                card_pool=card_pool,
                enabled=True,
                target_kinds=target_kinds,
            )
            if target_kinds
            else []
        )
        normalized_rules = sorted(
            (self._snapshot_rule(rule) for rule in rules),
            key=_snapshot_rule_sort_key,
        )
        body: dict[str, object] = {
            "schema_version": CLASSIFICATION_RULE_SNAPSHOT_SCHEMA_VERSION,
            "card_pool": card_pool,
            "rules": normalized_rules,
        }
        body["digest"] = _snapshot_digest(body)
        return body

    def validate_snapshot(
        self,
        value: object,
        *,
        card_pool: CardPool,
    ) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ClassificationRuleError("Classification rule snapshot must be an object.")
        if value.get("schema_version") not in SUPPORTED_CLASSIFICATION_RULE_SNAPSHOT_SCHEMA_VERSIONS:
            raise ClassificationRuleError("Unsupported classification rule snapshot schema.")
        if value.get("card_pool") != card_pool:
            raise ClassificationRuleError(
                "Classification rule snapshot pool does not match the job."
            )
        rules = value.get("rules")
        if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
            raise ClassificationRuleError("Classification rule snapshot rules must be an array.")
        expected_digest = _snapshot_digest(
            {
                "schema_version": value["schema_version"],
                "card_pool": value["card_pool"],
                "rules": rules,
            }
        )
        if value.get("digest") != expected_digest:
            raise ClassificationRuleError("Classification rule snapshot digest is invalid.")
        for rule in rules:
            rule_pool = str(rule.get("card_pool", ""))
            _validate_identity(
                card_pool=rule_pool,
                target_kind=str(rule.get("target_kind", "")),
                target_key=str(rule.get("target_key", "")),
            )
            if rule_pool != card_pool:
                raise ClassificationRuleError(
                    "Classification rule snapshot contains a rule from another pool."
                )
            if rule.get("source_kind") not in {
                CARD_CLASSIFICATION_SOURCE_TAG,
                CARD_CLASSIFICATION_SOURCE_TYPE,
                CARD_CLASSIFICATION_SOURCE_SYMBOL,
            }:
                raise ClassificationRuleError("Snapshot contains an unsupported source kind.")
            if not isinstance(rule.get("source_id"), str) or not rule["source_id"]:
                raise ClassificationRuleError("Snapshot rule source_id is required.")
            if not isinstance(rule.get("source_key"), str) or not rule["source_key"]:
                raise ClassificationRuleError("Snapshot rule source_key is required.")
            if not isinstance(rule.get("source_label"), str):
                raise ClassificationRuleError("Snapshot rule source_label must be a string.")
            source_identifiers = rule.get("source_identifiers")
            if not isinstance(source_identifiers, list) or not all(
                isinstance(identifier, str) for identifier in source_identifiers
            ):
                raise ClassificationRuleError(
                    "Snapshot rule source_identifiers must be an array of strings."
                )
            if not isinstance(rule.get("rule_id"), str) or not rule["rule_id"]:
                raise ClassificationRuleError("Snapshot rule rule_id is required.")
            if (
                value["schema_version"] >= 3
                and rule.get("source_kind") == CARD_CLASSIFICATION_SOURCE_SYMBOL
            ):
                _validate_snapshot_symbol(rule.get("source_symbol"))
        return cast(dict[str, object], value)

    def detector_sources_from_snapshot(
        self,
        value: object,
        *,
        card_pool: CardPool,
    ) -> tuple[list[Tag], list[Type], list[Symbol]]:
        snapshot = self.validate_snapshot(value, card_pool=card_pool)
        rules = cast(list[dict[str, object]], snapshot["rules"])
        tags: dict[str, Tag] = {}
        types: dict[str, Type] = {}
        symbols: dict[str, Symbol] = {}
        source_definitions: dict[tuple[str, str], object] = {}
        for rule in rules:
            source_kind = cast(str, rule["source_kind"])
            source_id = cast(str, rule["source_id"])
            source_key = cast(str, rule["source_key"])
            source_label = cast(str, rule["source_label"])
            source_identifiers = tuple(cast(list[str], rule["source_identifiers"]))
            identity = (source_kind, source_id)
            symbol_definition = rule.get("source_symbol")
            definition = (
                source_key,
                source_label,
                source_identifiers,
                symbol_definition,
            )
            previous = source_definitions.setdefault(identity, definition)
            if previous != definition:
                raise ClassificationRuleError(
                    "Snapshot contains conflicting definitions for one metadata source."
                )
            if source_kind == CARD_CLASSIFICATION_SOURCE_TAG:
                tags[source_id] = Tag(
                    id=source_id,
                    key=source_key,
                    label=source_label,
                    identifiers_json=list(source_identifiers),
                )
            elif source_kind == CARD_CLASSIFICATION_SOURCE_TYPE:
                types[source_id] = Type(
                    id=source_id,
                    key=source_key,
                    label=source_label,
                    identifiers_json=list(source_identifiers),
                )
            elif source_kind == CARD_CLASSIFICATION_SOURCE_SYMBOL and isinstance(
                symbol_definition, dict
            ) and symbol_definition["enabled"] is True and symbol_definition[
                "detector_type"
            ] == "template":
                symbols[source_id] = Symbol(
                    id=source_id,
                    key=source_key,
                    label=source_label,
                    symbol_type=cast(str, symbol_definition["symbol_type"]),
                    detector_type=cast(str, symbol_definition["detector_type"]),
                    detection_config_json=cast(
                        dict[str, object], symbol_definition["detection_config"]
                    ),
                    text_enrichment_json=cast(
                        dict[str, object], symbol_definition["text_enrichment"]
                    ),
                    reference_assets_json=cast(
                        list[str], symbol_definition["reference_assets"]
                    ),
                    text_token=cast(str, symbol_definition["text_token"]),
                    enabled=cast(bool, symbol_definition["enabled"]),
                )
        return (
            sorted(tags.values(), key=lambda source: (source.key, source.id)),
            sorted(types.values(), key=lambda source: (source.key, source.id)),
            sorted(symbols.values(), key=lambda source: (source.key, source.id)),
        )

    def definition_catalog(
        self, *, card_pool_scope: CardPoolScope
    ) -> dict[str, list[dict[str, object]]]:
        allowed_pools = tuple(
            definition.key
            for definition in CARD_POOL_DEFINITIONS
            if definition.key in card_pool_scope.allowed_pools
        )
        usage_counts = get_classification_usage_counts(card_pools=allowed_pools)
        display_symbol_keys = {
            key
            for key in (
                *(
                    definition.display_symbol_key
                    for definition in CARD_ROLE_DEFINITIONS
                ),
                *(definition.display_symbol_key for definition in CARD_FACTION_DEFINITIONS),
                *(definition.display_symbol_key for definition in MANA_FAMILIES),
            )
            if key is not None
        }
        symbols_by_key = {
            symbol.key: symbol
            for symbol in list_symbols(keys=display_symbol_keys)
        }
        rule_counts: dict[tuple[str, str, str, str], int] = defaultdict(int)
        rules_by_target: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
        for rule in list_classification_rules():
            if rule.card_pool not in allowed_pools:
                continue
            rule_counts[(rule.target_kind, rule.target_key, rule.card_pool, rule.source_kind)] += 1
            rules_by_target[(rule.target_kind, rule.target_key)].append(
                classification_rule_payload(rule)
            )

        def build_row(
            *,
            key: str,
            label: str,
            rank: int,
            target_kind: str,
            derived: bool,
            usage: dict[tuple[str, str], int] | None = None,
            derived_usage: dict[str, int] | None = None,
            display_symbol_key: str | None = None,
        ) -> dict[str, object]:
            return {
                "id": f"{target_kind}:{key}",
                "key": key,
                "label": label,
                "rank": rank,
                "target_kind": target_kind,
                "derived": derived,
                "linked_card_counts": {
                    pool: (derived_usage or {}).get(pool, 0)
                    if derived
                    else (usage or {}).get((key, pool), 0)
                    for pool in allowed_pools
                },
                "rule_counts": {
                    pool: {
                        source_kind: rule_counts[(target_kind, key, pool, source_kind)]
                        for source_kind in (
                            CARD_CLASSIFICATION_SOURCE_TAG,
                            CARD_CLASSIFICATION_SOURCE_TYPE,
                            CARD_CLASSIFICATION_SOURCE_SYMBOL,
                        )
                    }
                    for pool in allowed_pools
                },
                "rules": [] if derived else rules_by_target[(target_kind, key)],
                "display_symbol_key": display_symbol_key,
                "display_symbol": (
                    {
                        "id": symbols_by_key[display_symbol_key].id,
                        "key": symbols_by_key[display_symbol_key].key,
                        "label": symbols_by_key[display_symbol_key].label,
                    }
                    if display_symbol_key in symbols_by_key
                    else None
                ),
            }

        roles = [
            build_row(
                key=STANDARD_CARD_ROLE,
                label="Normal",
                rank=0,
                target_kind=CARD_CLASSIFICATION_TARGET_ROLE,
                derived=True,
                derived_usage=usage_counts.normal,
            ),
            *[
                build_row(
                    key=definition.key,
                    label=definition.label,
                    rank=definition.rank,
                    target_kind=CARD_CLASSIFICATION_TARGET_ROLE,
                    derived=False,
                    usage=usage_counts.roles,
                    display_symbol_key=definition.display_symbol_key,
                )
                for definition in CARD_ROLE_DEFINITIONS
            ],
        ]
        factions = [
            build_row(
                key="none",
                label="No faction",
                rank=0,
                target_kind=CARD_CLASSIFICATION_TARGET_FACTION,
                derived=True,
                derived_usage=usage_counts.no_faction,
            ),
            *[
                build_row(
                    key=definition.key,
                    label=definition.label,
                    rank=definition.rank,
                    target_kind=CARD_CLASSIFICATION_TARGET_FACTION,
                    derived=False,
                    usage=usage_counts.factions,
                    display_symbol_key=definition.display_symbol_key,
                )
                for definition in CARD_FACTION_DEFINITIONS
            ],
        ]
        mana_families = [
            build_row(
                key="none",
                label="Colorless",
                rank=-1,
                target_kind=CARD_CLASSIFICATION_TARGET_MANA_FAMILY,
                derived=True,
                derived_usage=usage_counts.colorless,
            ),
            *[
                build_row(
                    key=definition.key,
                    label=definition.label,
                    rank=definition.rank,
                    target_kind=CARD_CLASSIFICATION_TARGET_MANA_FAMILY,
                    derived=False,
                    usage=usage_counts.mana_families,
                    display_symbol_key=definition.display_symbol_key,
                )
                for definition in MANA_FAMILIES
            ],
        ]
        return {
            "roles": roles,
            "factions": factions,
            "mana_families": mana_families,
        }

    @staticmethod
    def _snapshot_rule(rule: CardClassificationRule) -> dict[str, object]:
        _validate_identity(
            card_pool=rule.card_pool,
            target_kind=rule.target_kind,
            target_key=rule.target_key,
        )
        payload = classification_rule_payload(rule)
        source = _rule_source(rule)
        if source is None:
            raise ClassificationRuleError(f"Rule {rule.id} has an invalid source reference.")
        snapshot_rule = {
            "rule_id": payload["id"],
            "card_pool": payload["card_pool"],
            "source_kind": payload["source_kind"],
            "source_id": payload["source_id"],
            "source_key": payload["source_key"],
            "source_label": source.label,
            "source_identifiers": list(getattr(source, "identifiers_json", [])),
            "target_kind": payload["target_kind"],
            "target_key": payload["target_key"],
        }
        if isinstance(source, Symbol):
            snapshot_rule["source_symbol"] = {
                "symbol_type": source.symbol_type,
                "detector_type": source.detector_type,
                "detection_config": source.detection_config_json,
                "text_enrichment": source.text_enrichment_json,
                "reference_assets": source.reference_assets_json,
                "text_token": source.text_token,
                "enabled": source.enabled,
            }
        return snapshot_rule


def _validate_snapshot_symbol(value: object) -> None:
    if not isinstance(value, dict):
        raise ClassificationRuleError("Snapshot Symbol detector definition is required.")
    for field in ("symbol_type", "detector_type", "text_token"):
        if not isinstance(value.get(field), str):
            raise ClassificationRuleError(
                f"Snapshot Symbol detector {field} must be a string."
            )
    for field in ("detection_config", "text_enrichment"):
        if not isinstance(value.get(field), dict):
            raise ClassificationRuleError(
                f"Snapshot Symbol detector {field} must be an object."
            )
    reference_assets = value.get("reference_assets")
    if not isinstance(reference_assets, list) or not all(
        isinstance(asset, str) for asset in reference_assets
    ):
        raise ClassificationRuleError(
            "Snapshot Symbol detector reference_assets must be an array of strings."
        )
    if not isinstance(value.get("enabled"), bool):
        raise ClassificationRuleError("Snapshot Symbol detector enabled must be a Boolean.")


def _snapshot_digest(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _snapshot_rule_sort_key(rule: dict[str, object]) -> tuple[int, int, int, str, str]:
    target_kind = str(rule["target_kind"])
    target_key = str(rule["target_key"])
    if target_kind == CARD_CLASSIFICATION_TARGET_ROLE:
        target_rank = next(
            definition.rank for definition in CARD_ROLE_DEFINITIONS if definition.key == target_key
        )
        target_kind_rank = 0
    elif target_kind == CARD_CLASSIFICATION_TARGET_FACTION:
        target_rank = next(
            definition.rank
            for definition in CARD_FACTION_DEFINITIONS
            if definition.key == target_key
        )
        target_kind_rank = 1
    else:
        target_rank = next(
            definition.rank
            for definition in MANA_FAMILIES
            if definition.key == target_key
        )
        target_kind_rank = 2
    source_kind = str(rule["source_kind"])
    source_kind_rank = {
        CARD_CLASSIFICATION_SOURCE_TAG: 0,
        CARD_CLASSIFICATION_SOURCE_TYPE: 1,
        CARD_CLASSIFICATION_SOURCE_SYMBOL: 2,
    }[source_kind]
    return (
        target_kind_rank,
        target_rank,
        source_kind_rank,
        str(rule["source_key"]),
        str(rule["rule_id"]),
    )

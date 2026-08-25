from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal, TypeVar, cast

from card_reader_core.models import (
    CARD_CLASSIFICATION_SOURCE_SYMBOL,
    CARD_CLASSIFICATION_SOURCE_TAG,
    CARD_CLASSIFICATION_SOURCE_TYPE,
    CARD_CLASSIFICATION_TARGET_FACTION,
    CARD_CLASSIFICATION_TARGET_MANA_FAMILY,
    CARD_CLASSIFICATION_TARGET_ROLE,
    CardClassificationInferenceEvidence,
    CardFaction,
    CardFactionInferenceEvidence,
    CardManaFamilyInferenceEvidence,
    CardPool,
    CardRole,
    CardRoleInferenceEvidence,
    ClassificationRuleEvidence,
    ClassificationSourceEvidence,
    normalize_card_factions,
    normalize_card_roles,
)
from card_reader_core.metadata import ManaFamily, normalize_mana_family_keys
from card_reader_core.services.classification_rules import ClassificationRuleService

CardClassificationMode = Literal["automatic", "override"]
_FacetValue = TypeVar("_FacetValue", CardRole, CardFaction, ManaFamily)


@dataclass(frozen=True)
class DetectedClassificationSource:
    id: str
    key: str


@dataclass(frozen=True)
class CardClassificationInput:
    card_pool: CardPool
    role_mode: CardClassificationMode
    override_roles: tuple[CardRole, ...]
    faction_mode: CardClassificationMode
    override_factions: tuple[CardFaction, ...]
    mana_family_mode: CardClassificationMode
    override_mana_families: tuple[ManaFamily, ...]
    rule_snapshot: dict[str, object]
    matched_tags: tuple[DetectedClassificationSource, ...]
    matched_types: tuple[DetectedClassificationSource, ...]
    matched_symbols: tuple[DetectedClassificationSource, ...]


@dataclass(frozen=True)
class CardClassificationResult:
    card_pool: CardPool
    roles: tuple[CardRole, ...]
    factions: tuple[CardFaction, ...]
    mana_families: tuple[ManaFamily, ...]
    evidence: CardClassificationInferenceEvidence


def _normalize_mana_family_values(values: Iterable[object]) -> tuple[ManaFamily, ...]:
    string_values = tuple(str(value) for value in values)
    return normalize_mana_family_keys(string_values)


def _resolve_facet(
    *,
    mode: CardClassificationMode,
    inferred_values: tuple[_FacetValue, ...],
    override_values: tuple[_FacetValue, ...],
    normalize: Callable[[Iterable[object]], tuple[_FacetValue, ...]],
    facet_label: str,
) -> tuple[_FacetValue, ...]:
    if mode == "override":
        return normalize(override_values)
    if mode == "automatic":
        return normalize(inferred_values)
    raise ValueError(f"Unsupported card {facet_label} mode: {mode}")


def classify_import_card(value: CardClassificationInput) -> CardClassificationResult:
    snapshot = ClassificationRuleService().validate_snapshot(
        value.rule_snapshot,
        card_pool=value.card_pool,
    )
    rules = cast(list[dict[str, object]], snapshot["rules"])
    digest = cast(str, snapshot["digest"])
    tags_by_id = {source.id: source for source in value.matched_tags}
    types_by_id = {source.id: source for source in value.matched_types}
    symbols_by_id = {source.id: source for source in value.matched_symbols}
    role_rules = (
        _matching_rules(
            rules,
            target_kind=CARD_CLASSIFICATION_TARGET_ROLE,
            tags_by_id=tags_by_id,
            types_by_id=types_by_id,
            symbols_by_id=symbols_by_id,
        )
        if value.role_mode == "automatic"
        else []
    )
    faction_rules = (
        _matching_rules(
            rules,
            target_kind=CARD_CLASSIFICATION_TARGET_FACTION,
            tags_by_id=tags_by_id,
            types_by_id=types_by_id,
            symbols_by_id=symbols_by_id,
        )
        if value.faction_mode == "automatic"
        else []
    )
    mana_family_rules = (
        _matching_rules(
            rules,
            target_kind=CARD_CLASSIFICATION_TARGET_MANA_FAMILY,
            tags_by_id=tags_by_id,
            types_by_id=types_by_id,
            symbols_by_id=symbols_by_id,
        )
        if value.mana_family_mode == "automatic"
        else []
    )
    inferred_roles = normalize_card_roles(rule["target_key"] for rule in role_rules)
    inferred_factions = normalize_card_factions(rule["target_key"] for rule in faction_rules)
    inferred_mana_families = normalize_mana_family_keys(
        tuple(str(rule["target_key"]) for rule in mana_family_rules)
    )
    override_roles = normalize_card_roles(value.override_roles)
    override_factions = normalize_card_factions(value.override_factions)
    override_mana_families = normalize_mana_family_keys(value.override_mana_families)
    resolved_roles = _resolve_facet(
        mode=value.role_mode,
        inferred_values=inferred_roles,
        override_values=override_roles,
        normalize=normalize_card_roles,
        facet_label="role",
    )
    resolved_factions = _resolve_facet(
        mode=value.faction_mode,
        inferred_values=inferred_factions,
        override_values=override_factions,
        normalize=normalize_card_factions,
        facet_label="faction",
    )
    resolved_mana_families = _resolve_facet(
        mode=value.mana_family_mode,
        inferred_values=inferred_mana_families,
        override_values=override_mana_families,
        normalize=_normalize_mana_family_values,
        facet_label="mana family",
    )
    role_evidence: CardRoleInferenceEvidence = {
        "mode": value.role_mode,
        "matched_tag_sources": _matched_source_evidence(role_rules, tags_by_id, "tag"),
        "matched_type_sources": _matched_source_evidence(role_rules, types_by_id, "type"),
        "matched_symbol_sources": _matched_source_evidence(
            role_rules, symbols_by_id, "symbol"
        ),
        "matched_rules": cast(list[ClassificationRuleEvidence], role_rules),
        "override_roles": list(override_roles) if value.role_mode == "override" else [],
        "resolved_roles": list(resolved_roles),
        "snapshot_digest": digest,
    }
    faction_evidence: CardFactionInferenceEvidence = {
        "mode": value.faction_mode,
        "matched_tag_sources": _matched_source_evidence(faction_rules, tags_by_id, "tag"),
        "matched_type_sources": _matched_source_evidence(faction_rules, types_by_id, "type"),
        "matched_symbol_sources": _matched_source_evidence(
            faction_rules, symbols_by_id, "symbol"
        ),
        "matched_rules": cast(list[ClassificationRuleEvidence], faction_rules),
        "override_factions": list(override_factions) if value.faction_mode == "override" else [],
        "resolved_factions": list(resolved_factions),
        "snapshot_digest": digest,
    }
    mana_family_evidence: CardManaFamilyInferenceEvidence = {
        "mode": value.mana_family_mode,
        "matched_tag_sources": _matched_source_evidence(mana_family_rules, tags_by_id, "tag"),
        "matched_type_sources": _matched_source_evidence(
            mana_family_rules, types_by_id, "type"
        ),
        "matched_symbol_sources": _matched_source_evidence(
            mana_family_rules, symbols_by_id, "symbol"
        ),
        "matched_rules": cast(list[ClassificationRuleEvidence], mana_family_rules),
        "override_mana_families": (
            list(override_mana_families) if value.mana_family_mode == "override" else []
        ),
        "resolved_mana_families": list(resolved_mana_families),
        "snapshot_digest": digest,
    }
    return CardClassificationResult(
        card_pool=value.card_pool,
        roles=resolved_roles,
        factions=resolved_factions,
        mana_families=resolved_mana_families,
        evidence={
            "roles": role_evidence,
            "factions": faction_evidence,
            "mana_families": mana_family_evidence,
        },
    )


def _matching_rules(
    rules: list[dict[str, object]],
    *,
    target_kind: str,
    tags_by_id: dict[str, DetectedClassificationSource],
    types_by_id: dict[str, DetectedClassificationSource],
    symbols_by_id: dict[str, DetectedClassificationSource],
) -> list[dict[str, object]]:
    matched: list[dict[str, object]] = []
    for rule in rules:
        if rule.get("target_kind") != target_kind:
            continue
        source_id = rule.get("source_id")
        source_kind = rule.get("source_kind")
        if not isinstance(source_id, str):
            continue
        if source_kind == CARD_CLASSIFICATION_SOURCE_TAG and source_id in tags_by_id:
            matched.append(rule)
        elif source_kind == CARD_CLASSIFICATION_SOURCE_TYPE and source_id in types_by_id:
            matched.append(rule)
        elif source_kind == CARD_CLASSIFICATION_SOURCE_SYMBOL and source_id in symbols_by_id:
            matched.append(rule)
    return matched


def _matched_source_evidence(
    rules: list[dict[str, object]],
    sources_by_id: dict[str, DetectedClassificationSource],
    source_kind: Literal["tag", "type", "symbol"],
) -> list[ClassificationSourceEvidence]:
    matched_ids = {
        cast(str, rule["source_id"])
        for rule in rules
        if rule.get("source_kind") == source_kind and rule.get("source_id") in sources_by_id
    }
    return [
        {"id": source.id, "key": source.key}
        for source in sorted(sources_by_id.values(), key=lambda item: (item.key, item.id))
        if source.id in matched_ids
    ]

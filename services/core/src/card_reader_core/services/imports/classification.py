from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal, TypeVar, cast

from card_reader_core.models import (
    BLOOD_CARD_FACTION,
    BOSS_CARD_ROLE,
    CARD_FACTIONS,
    CARD_ROLES,
    DARKNESS_CARD_FACTION,
    HERO_CARD_ROLE,
    LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION as CORE_LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION,
    LOCATION_CARD_ROLE,
    ORDER_CARD_FACTION,
    SHOP_ITEM_CARD_ROLE,
    CardClassificationInferenceEvidence,
    CardFaction,
    CardFactionInferenceEvidence,
    CardPool,
    CardRole,
    CardRoleInferenceEvidence,
    normalize_card_factions,
    normalize_card_roles,
)

SUPPORTED_CLASSIFICATION_INFERENCE_POLICY_VERSIONS = (1, 2, 3)
LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION = (
    CORE_LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION
)
CardClassificationMode = Literal["automatic", "override"]
_FacetValue = TypeVar("_FacetValue", CardRole, CardFaction)


@dataclass(frozen=True)
class CardClassificationInput:
    card_pool: CardPool
    role_mode: CardClassificationMode
    override_roles: tuple[CardRole, ...]
    template_roles: tuple[CardRole, ...]
    faction_mode: CardClassificationMode
    override_factions: tuple[CardFaction, ...]
    template_factions: tuple[CardFaction, ...]
    inference_policy_version: int
    matched_tag_keys: tuple[str, ...]


@dataclass(frozen=True)
class CardClassificationResult:
    card_pool: CardPool
    roles: tuple[CardRole, ...]
    factions: tuple[CardFaction, ...]
    evidence: CardClassificationInferenceEvidence


_TAG_ROLE_POLICIES: dict[int, dict[str, CardRole]] = {
    1: {"hero": HERO_CARD_ROLE},
    2: {"hero": HERO_CARD_ROLE, "location": LOCATION_CARD_ROLE},
    3: {
        "hero": HERO_CARD_ROLE,
        "boss": BOSS_CARD_ROLE,
        "location": LOCATION_CARD_ROLE,
        "shop-item": SHOP_ITEM_CARD_ROLE,
    },
}
_TAG_FACTION_POLICIES: dict[int, dict[str, CardFaction]] = {
    1: {},
    2: {},
    3: {
        "order": ORDER_CARD_FACTION,
        "blood": BLOOD_CARD_FACTION,
        "darkness": DARKNESS_CARD_FACTION,
    },
}


def _resolve_facet(
    *,
    mode: CardClassificationMode,
    template_values: tuple[_FacetValue, ...],
    override_values: tuple[_FacetValue, ...],
    tag_values: tuple[_FacetValue, ...],
    normalize: Callable[[Iterable[object]], tuple[_FacetValue, ...]],
    facet_label: str,
) -> tuple[_FacetValue, ...]:
    if mode == "override":
        return normalize(override_values)
    if mode == "automatic":
        return normalize((*template_values, *tag_values))
    raise ValueError(f"Unsupported card {facet_label} mode: {mode}")


def classify_import_card(value: CardClassificationInput) -> CardClassificationResult:
    role_policy = _TAG_ROLE_POLICIES.get(value.inference_policy_version)
    faction_policy = _TAG_FACTION_POLICIES.get(value.inference_policy_version)
    if role_policy is None or faction_policy is None:
        raise ValueError(
            "Unsupported card-classification inference policy version: "
            f"{value.inference_policy_version}"
        )

    template_roles = normalize_card_roles(value.template_roles)
    override_roles = normalize_card_roles(value.override_roles)
    template_factions = normalize_card_factions(value.template_factions)
    override_factions = normalize_card_factions(value.override_factions)
    matched_tag_keys = tuple(
        sorted({key.strip().lower() for key in value.matched_tag_keys if key.strip()})
    )
    tag_roles = normalize_card_roles(
        role_policy[key] for key in matched_tag_keys if key in role_policy
    )
    tag_factions = normalize_card_factions(
        faction_policy[key] for key in matched_tag_keys if key in faction_policy
    )
    resolved_roles = _resolve_facet(
        mode=value.role_mode,
        template_values=template_roles,
        override_values=override_roles,
        tag_values=tag_roles,
        normalize=normalize_card_roles,
        facet_label="role",
    )
    resolved_factions = _resolve_facet(
        mode=value.faction_mode,
        template_values=template_factions,
        override_values=override_factions,
        tag_values=tag_factions,
        normalize=normalize_card_factions,
        facet_label="faction",
    )

    role_evidence: CardRoleInferenceEvidence = {
        "mode": value.role_mode,
        "policy_version": value.inference_policy_version,
        "template_roles": list(template_roles),
        "matched_tag_keys": list(matched_tag_keys),
        "tag_roles": list(tag_roles),
        "override_roles": list(override_roles) if value.role_mode == "override" else [],
        "resolved_roles": list(resolved_roles),
    }
    faction_evidence: CardFactionInferenceEvidence = {
        "mode": value.faction_mode,
        "policy_version": value.inference_policy_version,
        "template_factions": list(template_factions),
        "matched_tag_keys": list(matched_tag_keys),
        "tag_factions": list(tag_factions),
        "override_factions": (
            list(override_factions) if value.faction_mode == "override" else []
        ),
        "resolved_factions": list(resolved_factions),
    }
    return CardClassificationResult(
        card_pool=value.card_pool,
        roles=resolved_roles,
        factions=resolved_factions,
        evidence={"roles": role_evidence, "factions": faction_evidence},
    )


def normalize_classification_mode(
    value: object,
    *,
    field_name: str,
) -> CardClassificationMode:
    if value not in {"automatic", "override"}:
        raise ValueError(f"{field_name} must be either 'automatic' or 'override'.")
    return cast(CardClassificationMode, value)


def validate_inference_policy_version(value: int) -> int:
    if value not in SUPPORTED_CLASSIFICATION_INFERENCE_POLICY_VERSIONS:
        raise ValueError(f"Unsupported card-classification inference policy version: {value}")
    return value


def validate_card_roles(values: object, *, field_name: str) -> tuple[CardRole, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field_name} must be an array.")
    invalid = sorted({str(value) for value in values if value not in CARD_ROLES})
    if invalid:
        raise ValueError(f"{field_name} contains unsupported roles: {', '.join(invalid)}")
    return normalize_card_roles(values)


def validate_card_factions(values: object, *, field_name: str) -> tuple[CardFaction, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field_name} must be an array.")
    invalid = sorted({str(value) for value in values if value not in CARD_FACTIONS})
    if invalid:
        raise ValueError(f"{field_name} contains unsupported factions: {', '.join(invalid)}")
    return normalize_card_factions(values)

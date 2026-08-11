from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from card_reader_core.models import (
    CARD_ROLES,
    HERO_CARD_ROLE,
    LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION as CORE_LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION,
    LOCATION_CARD_ROLE,
    CardPool,
    CardRole,
    CardRoleInferenceEvidence,
    normalize_card_roles,
)

SUPPORTED_CARD_ROLE_INFERENCE_POLICY_VERSIONS = (1, 2)
LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION = CORE_LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION
CardRoleMode = Literal["automatic", "override"]


@dataclass(frozen=True)
class CardClassificationInput:
    card_pool: CardPool
    role_mode: CardRoleMode
    override_roles: tuple[CardRole, ...]
    template_roles: tuple[CardRole, ...]
    inference_policy_version: int
    matched_tag_keys: tuple[str, ...]


@dataclass(frozen=True)
class CardClassificationResult:
    card_pool: CardPool
    roles: tuple[CardRole, ...]
    evidence: CardRoleInferenceEvidence


_TAG_ROLE_POLICIES: dict[int, dict[str, CardRole]] = {
    1: {"hero": HERO_CARD_ROLE},
    2: {"hero": HERO_CARD_ROLE, "location": LOCATION_CARD_ROLE},
}


def classify_import_card(value: CardClassificationInput) -> CardClassificationResult:
    policy = _TAG_ROLE_POLICIES.get(value.inference_policy_version)
    if policy is None:
        raise ValueError(
            f"Unsupported card-role inference policy version: {value.inference_policy_version}"
        )

    template_roles = normalize_card_roles(value.template_roles)
    override_roles = normalize_card_roles(value.override_roles)
    matched_tag_keys = tuple(sorted({key.strip().lower() for key in value.matched_tag_keys if key.strip()}))
    tag_roles = normalize_card_roles(policy[key] for key in matched_tag_keys if key in policy)

    if value.role_mode == "override":
        resolved_roles = override_roles
    elif value.role_mode == "automatic":
        resolved_roles = normalize_card_roles((*template_roles, *tag_roles))
    else:
        raise ValueError(f"Unsupported card role mode: {value.role_mode}")

    evidence: CardRoleInferenceEvidence = {
        "mode": value.role_mode,
        "policy_version": value.inference_policy_version,
        "template_roles": list(template_roles),
        "matched_tag_keys": list(matched_tag_keys),
        "tag_roles": list(tag_roles),
        "override_roles": list(override_roles) if value.role_mode == "override" else [],
        "resolved_roles": list(resolved_roles),
    }
    return CardClassificationResult(
        card_pool=value.card_pool,
        roles=resolved_roles,
        evidence=evidence,
    )


def normalize_role_mode(value: object) -> CardRoleMode:
    if value not in {"automatic", "override"}:
        raise ValueError("card_role_mode must be either 'automatic' or 'override'.")
    return cast(CardRoleMode, value)


def validate_inference_policy_version(value: int) -> int:
    if value not in SUPPORTED_CARD_ROLE_INFERENCE_POLICY_VERSIONS:
        raise ValueError(f"Unsupported card-role inference policy version: {value}")
    return value


def validate_card_roles(values: object, *, field_name: str) -> tuple[CardRole, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field_name} must be an array.")
    invalid = sorted({str(value) for value in values if value not in CARD_ROLES})
    if invalid:
        raise ValueError(f"{field_name} contains unsupported roles: {', '.join(invalid)}")
    return normalize_card_roles(values)

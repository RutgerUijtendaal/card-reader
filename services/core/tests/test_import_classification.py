from __future__ import annotations

import hashlib
import json

import pytest

from card_reader_core.services.imports import (
    CardClassificationInput,
    DetectedClassificationSource,
    classify_import_card,
)


def rule(
    rule_id: str,
    *,
    target_kind: str,
    target_key: str,
    source_kind: str,
    source_id: str,
    source_key: str,
    card_pool: str = "evil",
) -> dict[str, object]:
    return {
        "rule_id": rule_id,
        "card_pool": card_pool,
        "target_kind": target_kind,
        "target_key": target_key,
        "source_kind": source_kind,
        "source_id": source_id,
        "source_key": source_key,
        "source_label": source_key,
        "source_identifiers": [],
    }


def snapshot(*rules: dict[str, object], card_pool: str = "evil") -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": 1,
        "card_pool": card_pool,
        "rules": list(rules),
    }
    body["digest"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return body


def classification_input(
    *,
    rules: tuple[dict[str, object], ...] = (),
    role_mode: str = "automatic",
    role_override: tuple[str, ...] = (),
    faction_mode: str = "automatic",
    faction_override: tuple[str, ...] = (),
    tags: tuple[tuple[str, str], ...] = (),
    types: tuple[tuple[str, str], ...] = (),
) -> CardClassificationInput:
    return CardClassificationInput(
        card_pool="evil",
        role_mode=role_mode,  # type: ignore[arg-type]
        override_roles=role_override,  # type: ignore[arg-type]
        faction_mode=faction_mode,  # type: ignore[arg-type]
        override_factions=faction_override,  # type: ignore[arg-type]
        rule_snapshot=snapshot(*rules),
        matched_tags=tuple(DetectedClassificationSource(id=id_, key=key) for id_, key in tags),
        matched_types=tuple(DetectedClassificationSource(id=id_, key=key) for id_, key in types),
    )


def test_automatic_inference_unions_tag_and_type_rules_canonically() -> None:
    rules = (
        rule(
            "rule-event",
            target_kind="role",
            target_key="event",
            source_kind="type",
            source_id="type-event",
            source_key="event",
        ),
        rule(
            "rule-boss",
            target_kind="role",
            target_key="boss",
            source_kind="tag",
            source_id="tag-boss",
            source_key="boss",
        ),
        rule(
            "rule-order-tag",
            target_kind="faction",
            target_key="order",
            source_kind="tag",
            source_id="tag-order",
            source_key="order",
        ),
        rule(
            "rule-order-type",
            target_kind="faction",
            target_key="order",
            source_kind="type",
            source_id="type-order",
            source_key="order-card",
        ),
    )
    result = classify_import_card(
        classification_input(
            rules=rules,
            tags=(("tag-order", "order"), ("tag-boss", "boss")),
            types=(("type-event", "event"), ("type-order", "order-card")),
        )
    )

    assert result.roles == ("boss", "event")
    assert result.factions == ("order",)
    assert result.evidence["roles"]["matched_tag_sources"] == [{"id": "tag-boss", "key": "boss"}]
    assert result.evidence["roles"]["matched_type_sources"] == [
        {"id": "type-event", "key": "event"}
    ]
    assert {item["rule_id"] for item in result.evidence["factions"]["matched_rules"]} == {
        "rule-order-tag",
        "rule-order-type",
    }


def test_role_and_faction_overrides_are_independent_and_exact() -> None:
    rules = (
        rule(
            "rule-boss",
            target_kind="role",
            target_key="boss",
            source_kind="tag",
            source_id="tag-boss",
            source_key="boss",
        ),
        rule(
            "rule-order",
            target_kind="faction",
            target_key="order",
            source_kind="tag",
            source_id="tag-order",
            source_key="order",
        ),
    )
    role_override = classify_import_card(
        classification_input(
            rules=rules,
            role_mode="override",
            role_override=("boon",),
            tags=(("tag-boss", "boss"), ("tag-order", "order")),
        )
    )
    faction_override = classify_import_card(
        classification_input(
            rules=rules,
            faction_mode="override",
            faction_override=(),
            tags=(("tag-boss", "boss"), ("tag-order", "order")),
        )
    )

    assert role_override.roles == ("boon",)
    assert role_override.factions == ("order",)
    assert role_override.evidence["roles"]["matched_rules"] == []
    assert faction_override.roles == ("boss",)
    assert faction_override.factions == ()
    assert faction_override.evidence["factions"]["matched_rules"] == []


def test_unmatched_rules_are_a_resolved_empty_classification() -> None:
    result = classify_import_card(
        classification_input(
            rules=(
                rule(
                    "rule-boss",
                    target_kind="role",
                    target_key="boss",
                    source_kind="tag",
                    source_id="tag-boss",
                    source_key="boss",
                ),
            ),
        )
    )

    assert result.roles == ()
    assert result.factions == ()
    assert result.evidence["roles"]["resolved_roles"] == []
    assert result.evidence["factions"]["resolved_factions"] == []


def test_snapshot_pool_and_digest_are_validated() -> None:
    value = classification_input()
    value.rule_snapshot["digest"] = "tampered"

    with pytest.raises(ValueError, match="snapshot digest is invalid"):
        classify_import_card(value)


def test_snapshot_rejects_a_valid_rule_from_another_pool() -> None:
    value = classification_input(
        rules=(
            rule(
                "player-hero-rule",
                target_kind="role",
                target_key="hero",
                source_kind="tag",
                source_id="hero-tag",
                source_key="hero",
                card_pool="player",
            ),
        ),
        tags=(("hero-tag", "hero"),),
    )

    with pytest.raises(ValueError, match="rule from another pool"):
        classify_import_card(value)

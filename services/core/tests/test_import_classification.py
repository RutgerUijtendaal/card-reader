from __future__ import annotations

import pytest

from card_reader_core.services.imports import CardClassificationInput, classify_import_card


def classification_input(
    *,
    policy: int,
    role_mode: str = "automatic",
    roles: tuple[str, ...] = (),
    role_override: tuple[str, ...] = (),
    faction_mode: str = "automatic",
    factions: tuple[str, ...] = (),
    faction_override: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> CardClassificationInput:
    return CardClassificationInput(
        card_pool="evil",
        role_mode=role_mode,  # type: ignore[arg-type]
        override_roles=role_override,  # type: ignore[arg-type]
        template_roles=roles,  # type: ignore[arg-type]
        faction_mode=faction_mode,  # type: ignore[arg-type]
        override_factions=faction_override,  # type: ignore[arg-type]
        template_factions=factions,  # type: ignore[arg-type]
        inference_policy_version=policy,
        matched_tag_keys=tags,
    )


def test_policy_versions_preserve_historical_role_and_faction_behavior() -> None:
    version_one = classify_import_card(
        classification_input(policy=1, tags=("location", "hero", "order"))
    )
    version_two = classify_import_card(
        classification_input(
            policy=2,
            roles=("event", "location"),
            tags=("location", "hero", "order"),
        )
    )

    assert version_one.roles == ("hero",)
    assert version_one.factions == ()
    assert version_one.evidence["roles"]["tag_roles"] == ["hero"]
    assert version_two.roles == ("hero", "location", "event")
    assert version_two.factions == ()
    assert version_two.evidence["roles"]["tag_roles"] == ["hero", "location"]


def test_policy_three_unions_and_orders_role_and_faction_signals() -> None:
    result = classify_import_card(
        classification_input(
            policy=3,
            roles=("event", "boon"),
            factions=("darkness",),
            tags=("order", "shop-item", "boss", "hero", "order"),
        )
    )

    assert result.roles == ("hero", "boss", "boon", "event", "shop_item")
    assert result.factions == ("order", "darkness")
    assert result.evidence["roles"]["matched_tag_keys"] == [
        "boss",
        "hero",
        "order",
        "shop-item",
    ]
    assert result.evidence["factions"]["tag_factions"] == ["order"]


def test_role_and_faction_overrides_are_independent_and_exact() -> None:
    role_override = classify_import_card(
        classification_input(
            policy=3,
            role_mode="override",
            role_override=("boon",),
            factions=("blood",),
            tags=("hero", "order"),
        )
    )
    faction_override = classify_import_card(
        classification_input(
            policy=3,
            roles=("event",),
            faction_mode="override",
            faction_override=(),
            factions=("blood",),
            tags=("hero", "order"),
        )
    )

    assert role_override.roles == ("boon",)
    assert role_override.factions == ("order", "blood")
    assert role_override.evidence["roles"]["mode"] == "override"
    assert faction_override.roles == ("hero", "event")
    assert faction_override.factions == ()
    assert faction_override.evidence["factions"]["mode"] == "override"


def test_empty_role_and_faction_results_are_explicit_empty_facets() -> None:
    result = classify_import_card(classification_input(policy=3))

    assert result.roles == ()
    assert result.factions == ()
    assert result.evidence["roles"]["resolved_roles"] == []
    assert result.evidence["factions"]["resolved_factions"] == []


def test_unknown_inference_policy_is_not_reinterpreted_as_latest() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported card-classification inference policy version",
    ):
        classify_import_card(classification_input(policy=999, tags=("hero",)))

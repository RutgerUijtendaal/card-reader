from __future__ import annotations

import pytest

from card_reader_core.services.imports import CardClassificationInput, classify_import_card


def test_automatic_import_classification_unions_template_and_tag_roles_canonically() -> None:
    result = classify_import_card(
        CardClassificationInput(
            card_pool="game_master",
            role_mode="automatic",
            override_roles=(),
            template_roles=("event", "boon"),
            inference_policy_version=1,
            matched_tag_keys=("hero", "hero"),
        )
    )

    assert result.card_pool == "game_master"
    assert result.roles == ("hero", "boon", "event")
    assert result.evidence["matched_tag_keys"] == ["hero"]


def test_policy_version_two_infers_location_without_reinterpreting_version_one() -> None:
    version_one = classify_import_card(
        CardClassificationInput(
            card_pool="game_master",
            role_mode="automatic",
            override_roles=(),
            template_roles=(),
            inference_policy_version=1,
            matched_tag_keys=("location", "hero"),
        )
    )
    version_two = classify_import_card(
        CardClassificationInput(
            card_pool="game_master",
            role_mode="automatic",
            override_roles=(),
            template_roles=("event", "location"),
            inference_policy_version=2,
            matched_tag_keys=("location", "hero", "location"),
        )
    )

    assert version_one.roles == ("hero",)
    assert version_one.evidence["tag_roles"] == ["hero"]
    assert version_two.roles == ("hero", "event", "location")
    assert version_two.evidence["matched_tag_keys"] == ["hero", "location"]
    assert version_two.evidence["tag_roles"] == ["hero", "location"]


def test_import_role_override_replaces_all_automatic_signals() -> None:
    result = classify_import_card(
        CardClassificationInput(
            card_pool="player",
            role_mode="override",
            override_roles=("boon",),
            template_roles=("event",),
            inference_policy_version=2,
            matched_tag_keys=("hero", "location"),
        )
    )

    assert result.roles == ("boon",)
    assert result.evidence["mode"] == "override"


def test_empty_automatic_and_override_results_are_standard() -> None:
    automatic = classify_import_card(
        CardClassificationInput(
            card_pool="player",
            role_mode="automatic",
            override_roles=(),
            template_roles=(),
            inference_policy_version=2,
            matched_tag_keys=(),
        )
    )
    override = classify_import_card(
        CardClassificationInput(
            card_pool="player",
            role_mode="override",
            override_roles=(),
            template_roles=("event",),
            inference_policy_version=2,
            matched_tag_keys=("hero", "location"),
        )
    )

    assert automatic.roles == ()
    assert override.roles == ()


def test_unknown_inference_policy_is_not_reinterpreted_as_latest() -> None:
    with pytest.raises(ValueError, match="Unsupported card-role inference policy version"):
        classify_import_card(
            CardClassificationInput(
                card_pool="player",
                role_mode="automatic",
                override_roles=(),
                template_roles=(),
                inference_policy_version=999,
                matched_tag_keys=("hero",),
            )
        )

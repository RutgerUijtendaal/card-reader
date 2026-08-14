from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.test import Client

from card_reader_core.models import (
    EVIL_CARD_POOL,
    PLAYER_CARD_POOL,
    Card,
    CardVersion,
    CardVersionParseFlag,
    ParseResult,
    Template,
)


def test_authenticated_user_can_create_parse_flag_with_multiple_items() -> None:
    _clear_parse_flags()
    user = _create_user("parse-flag-user", "password", is_staff=False)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    card, version = _create_card_version(name="Flagged Card")

    response = client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={
            "note": "Several fields look wrong.",
            "items": [
                {"property_key": "name", "expected_value": "Correct Name", "note": "Name OCR drift."},
                {"property_key": "rules_text", "expected_value": "Correct rules"},
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["card_version_id"] == version.id
    assert payload["item_count"] == 2

    review_client = Client(HTTP_HOST="localhost")
    review_client.force_login(_create_user("parse-flag-reviewer", "password", is_staff=True))
    list_response = review_client.get("/review/parse-flags?page_size=1")

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["count"] == 1
    results = list_payload["results"]
    report = next(row for row in results if row["id"] == payload["id"])
    assert {row["property_key"] for row in report["items"]} == {"name", "rules_text"}
    name_item = next(row for row in report["items"] if row["property_key"] == "name")
    assert name_item["captured_current_value"] == "Flagged Card"
    assert name_item["expected_value"] == "Correct Name"
    assert report["submitted_by"]["username"] == "parse-flag-user"


def test_anonymous_user_cannot_create_parse_flag() -> None:
    _clear_parse_flags()
    card, version = _create_card_version(name="Anonymous Flag Card")

    response = Client(HTTP_HOST="localhost").post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={"items": [{"property_key": "name"}]},
        content_type="application/json",
    )

    assert response.status_code in {401, 403}


def test_evil_parse_flags_follow_the_central_access_capability() -> None:
    _clear_parse_flags()
    card, version = _create_card_version(
        name="Restricted Flag Card",
        card_pool=EVIL_CARD_POOL,
    )
    regular_client = Client(HTTP_HOST="localhost")
    regular_client.force_login(_create_user("restricted-flag-user", "password", is_staff=False))
    staff_client = Client(HTTP_HOST="localhost")
    staff_client.force_login(_create_user("restricted-flag-staff", "password", is_staff=True))
    payload = {"items": [{"property_key": "name", "expected_value": "Correct name"}]}

    regular_response = regular_client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data=payload,
        content_type="application/json",
    )
    staff_response = staff_client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data=payload,
        content_type="application/json",
    )

    assert regular_response.status_code == 404
    assert staff_response.status_code == 201


def test_parse_flag_review_list_is_scoped_to_one_explicit_card_pool() -> None:
    _clear_parse_flags()
    reviewer = _create_user("pool-scoped-flag-reviewer", "password", is_staff=True)
    client = Client(HTTP_HOST="localhost")
    client.force_login(reviewer)
    player_card, player_version = _create_card_version(name="Player Review Flag")
    evil_card, evil_version = _create_card_version(
        name="Evil Review Flag",
        card_pool=EVIL_CARD_POOL,
    )
    payload = {"items": [{"property_key": "name", "expected_value": "Correct name"}]}
    assert (
        client.post(
            f"/cards/{player_card.id}/versions/{player_version.id}/flags",
            data=payload,
            content_type="application/json",
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/cards/{evil_card.id}/versions/{evil_version.id}/flags",
            data=payload,
            content_type="application/json",
        ).status_code
        == 201
    )

    player_response = client.get(f"/review/parse-flags?card_pool={PLAYER_CARD_POOL}")
    evil_response = client.get(f"/review/parse-flags?card_pool={EVIL_CARD_POOL}")
    default_response = client.get("/review/parse-flags")
    obsolete_response = client.get("/review/parse-flags?card_pool=game_master")

    assert player_response.status_code == 200
    assert [row["card"]["name"] for row in player_response.json()["results"]] == [
        "Player Review Flag"
    ]
    assert evil_response.status_code == 200
    assert [row["card"]["name"] for row in evil_response.json()["results"]] == [
        "Evil Review Flag"
    ]
    assert default_response.json()["results"][0]["card"]["name"] == "Player Review Flag"
    assert obsolete_response.status_code == 400


def test_authenticated_user_can_create_overall_and_property_flag_items() -> None:
    _clear_parse_flags()
    user = _create_user("parse-flag-overall-user", "password", is_staff=False)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    card, version = _create_card_version(name="Overall Flag Card")

    response = client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={
            "note": "Shared context.",
            "items": [
                {"property_key": "overall", "note": "The card should have a clearer identity."},
                {"property_key": "name", "expected_value": "Clearer Card Name"},
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["item_count"] == 2

    review_client = Client(HTTP_HOST="localhost")
    review_client.force_login(_create_user("parse-flag-overall-reviewer", "password", is_staff=True))
    report = review_client.get("/review/parse-flags").json()["results"][0]
    overall_item = next(item for item in report["items"] if item["property_key"] == "overall")
    assert overall_item["captured_current_value"] == ""
    assert overall_item["expected_value"] == ""
    assert overall_item["note"] == "The card should have a clearer identity."


def test_parse_flag_rejects_blank_overall_suggestion() -> None:
    _clear_parse_flags()
    user = _create_user("parse-flag-blank-overall-user", "password", is_staff=False)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    card, version = _create_card_version(name="Blank Overall Flag Card")

    response = client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={"items": [{"property_key": "overall", "note": "   "}]},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert CardVersionParseFlag.objects.count() == 0


def test_parse_flag_rejects_property_without_expected_value() -> None:
    _clear_parse_flags()
    user = _create_user("parse-flag-blank-property-user", "password", is_staff=False)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    card, version = _create_card_version(name="Blank Property Flag Card")

    response = client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={"items": [{"property_key": "name", "note": "The name looks wrong."}]},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert CardVersionParseFlag.objects.count() == 0


def test_parse_flag_requires_real_user() -> None:
    _clear_parse_flags()
    card, version = _create_card_version(name="Unauthenticated Flag Card")

    response = Client(HTTP_HOST="localhost").post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={"items": [{"property_key": "name"}]},
        content_type="application/json",
    )

    assert response.status_code in {401, 403}


def test_parse_flag_rejects_invalid_card_version_pairing_and_property() -> None:
    _clear_parse_flags()
    user = _create_user("parse-flag-invalid-user", "password", is_staff=False)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    first_card, _first_version = _create_card_version(name="First Invalid Card")
    _second_card, second_version = _create_card_version(name="Second Invalid Card")

    pairing_response = client.post(
        f"/cards/{first_card.id}/versions/{second_version.id}/flags",
        data={"items": [{"property_key": "name", "expected_value": "Correct name"}]},
        content_type="application/json",
    )
    property_response = client.post(
        f"/cards/{first_card.id}/versions/{_first_version.id}/flags",
        data={"items": [{"property_key": "not_a_property"}]},
        content_type="application/json",
    )

    assert pairing_response.status_code == 404
    assert property_response.status_code == 400


def test_staff_can_resolve_and_dismiss_parse_flag_items() -> None:
    _clear_parse_flags()
    submitter = _create_user("parse-flag-submit-status", "password", is_staff=False)
    reviewer = _create_user("parse-flag-review-status", "password", is_staff=True)
    card, version = _create_card_version(name="Status Flag Card")
    submit_client = Client(HTTP_HOST="localhost")
    submit_client.force_login(submitter)
    submit_response = submit_client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={
            "items": [
                {"property_key": "name", "expected_value": "Corrected name"},
                {
                    "property_key": "other",
                    "expected_value": "Use the centered template",
                    "note": "Template looks offset.",
                },
            ],
        },
        content_type="application/json",
    )
    assert submit_response.status_code == 201

    regular_client = Client(HTTP_HOST="localhost")
    regular_client.force_login(submitter)
    assert regular_client.get("/review/parse-flags").status_code == 403

    review_client = Client(HTTP_HOST="localhost")
    review_client.force_login(reviewer)
    list_response = review_client.get("/review/parse-flags")
    reports = list_response.json()["results"]
    assert len(reports) == 1
    ids = [row["id"] for row in reports[0]["items"]]

    resolve_response = review_client.patch(
        f"/review/parse-flags/items/{ids[0]}",
        data={"status": "resolved", "review_note": "Fixed in editor."},
        content_type="application/json",
    )
    dismiss_response = review_client.patch(
        f"/review/parse-flags/items/{ids[1]}",
        data={"status": "dismissed"},
        content_type="application/json",
    )
    summary_response = review_client.get("/review/summary")

    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved"
    assert resolve_response.json()["review_note"] == "Fixed in editor."
    assert dismiss_response.status_code == 200
    assert dismiss_response.json()["status"] == "dismissed"
    assert summary_response.status_code == 200
    assert summary_response.json()["open_parse_flag_item_count"] == 0


def _create_user(
    username: str,
    password: str,
    *,
    is_staff: bool,
):
    user_model = get_user_model()
    user_model.objects.filter(username=username).delete()
    user = user_model.objects.create_user(username=username, password=password)
    user.is_staff = is_staff
    user.save(update_fields=["is_staff"])
    return user


def _clear_parse_flags() -> None:
    CardVersionParseFlag.objects.all().delete()


def _create_card_version(*, name: str, card_pool: str = "player") -> tuple[Card, CardVersion]:
    template = Template.objects.get(key="mtg-like-v1")
    card = Card.objects.create(
        key=name.lower().replace(" ", "-"),
        label=name,
        card_pool=card_pool,
    )
    version = CardVersion.objects.create(
        card=card,
        version_number=1,
        template=template,
        image_hash=f"hash-{name}",
        name=name,
        type_line="Base Type",
        mana_cost="2",
        mana_symbols_json=[],
        mana_value=2,
        rules_text_raw="Base rules",
        rules_text_enriched="Base rules",
        rules_text="Base rules",
        confidence=0.9,
        field_sources_json=json.dumps(
            {
                "fields": {
                    "name": "auto",
                    "type_line": "auto",
                    "mana_cost": "auto",
                    "attack": "auto",
                    "health": "auto",
                    "rules_text": "auto",
                },
                "metadata": {
                    "keywords": "auto",
                    "tags": "auto",
                    "types": "auto",
                    "symbols": "auto",
                },
            }
        ),
        parsed_snapshot_json=json.dumps(
            {
                "fields": {
                    "name": name,
                    "type_line": "Base Type",
                    "mana_cost": "2",
                    "attack": None,
                    "health": None,
                    "rules_text": "Base rules",
                },
                "metadata": {
                    "keyword_ids": [],
                    "tag_ids": [],
                    "type_ids": [],
                    "symbol_ids": [],
                },
            }
        ),
        is_latest=True,
    )
    ParseResult.objects.create(
        card_version=version,
        raw_ocr_json={},
        normalized_fields_json={},
        confidence_json={},
    )
    card.latest_version = version
    card.save(update_fields=["latest_version"])
    return card, version

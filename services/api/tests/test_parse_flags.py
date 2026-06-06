from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from card_reader_core.models import Card, CardVersion, CardVersionParseFlag, ParseResult, Template


@override_settings(CARD_READER_AUTH_ENABLED=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_anonymous_user_cannot_create_parse_flag() -> None:
    _clear_parse_flags()
    card, version = _create_card_version(name="Anonymous Flag Card")

    response = Client(HTTP_HOST="localhost").post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={"items": [{"property_key": "name"}]},
        content_type="application/json",
    )

    assert response.status_code in {401, 403}


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_parse_flag_still_requires_real_user_when_auth_is_disabled() -> None:
    _clear_parse_flags()
    card, version = _create_card_version(name="Auth Disabled Flag Card")

    response = Client(HTTP_HOST="localhost").post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={"items": [{"property_key": "name"}]},
        content_type="application/json",
    )

    assert response.status_code in {401, 403}


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_parse_flag_rejects_invalid_card_version_pairing_and_property() -> None:
    _clear_parse_flags()
    user = _create_user("parse-flag-invalid-user", "password", is_staff=False)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    first_card, _first_version = _create_card_version(name="First Invalid Card")
    _second_card, second_version = _create_card_version(name="Second Invalid Card")

    pairing_response = client.post(
        f"/cards/{first_card.id}/versions/{second_version.id}/flags",
        data={"items": [{"property_key": "name"}]},
        content_type="application/json",
    )
    property_response = client.post(
        f"/cards/{first_card.id}/versions/{_first_version.id}/flags",
        data={"items": [{"property_key": "not_a_property"}]},
        content_type="application/json",
    )

    assert pairing_response.status_code == 404
    assert property_response.status_code == 400


@override_settings(CARD_READER_AUTH_ENABLED=True)
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
                {"property_key": "name"},
                {"property_key": "other", "note": "Template looks offset."},
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


def _create_card_version(*, name: str) -> tuple[Card, CardVersion]:
    template = Template.objects.get(key="mtg-like-v1")
    card = Card.objects.create(key=name.lower().replace(" ", "-"), label=name)
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

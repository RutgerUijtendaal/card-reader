from __future__ import annotations

from collections.abc import Iterable
from itertools import count

from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from card_reader_core.models import Card, CardVersion, CardVersionType, Deck, ParseResult, Template, Type
from card_reader_core.services.decks import DeckEntryInput, DeckService

_CARD_NAME_COUNTER = count()


def _template_definition() -> dict[str, object]:
    return {
        "id": "deck-test-template",
        "version": 1,
        "regions": [
            {
                "region_id": "top_bar",
                "parser_type": "name_mana_cost",
                "cut_region": {"unit": "relative", "x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
                "ocr_config": {},
            }
        ],
    }


def _ensure_template() -> Template:
    template, _created = Template.objects.get_or_create(
        key="deck-test-template",
        defaults={"label": "Deck Test Template", "definition_json": _template_definition()},
    )
    return template


def _create_user(username: str, password: str, *, is_staff: bool = False):
    user_model = get_user_model()
    user_model.objects.filter(username=username).delete()
    user = user_model.objects.create_user(username=username, password=password)
    user.is_staff = is_staff
    user.save(update_fields=["is_staff"])
    return user


def _login_and_get_csrf_token(client: Client, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    csrf_token = response.json()["csrf_token"]
    assert isinstance(csrf_token, str)
    return csrf_token


def _create_card(*, name: str, is_hero: bool, type_labels: list[str] | None = None) -> Card:
    template = _ensure_template()
    unique_name = f"{name} {next(_CARD_NAME_COUNTER)}"
    card = Card.objects.create(
        key=unique_name.lower().replace(" ", "-"),
        label=unique_name,
        is_hero=is_hero,
    )
    version = CardVersion.objects.create(
        card=card,
        version_number=1,
        template=template,
        image_hash=f"hash-{unique_name}",
        name=unique_name,
        type_line="Hero" if is_hero else "Follower",
        mana_cost="",
        mana_symbols_json=[],
        rules_text_raw="",
        rules_text_enriched="",
        rules_text="",
        confidence=1.0,
        field_sources_json={
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
        },
        parsed_snapshot_json={
            "fields": {
                "name": name,
                "type_line": "Hero" if is_hero else "Follower",
                "mana_cost": "",
                "attack": None,
                "health": None,
                "rules_text": "",
            },
            "metadata": {"keyword_ids": [], "tag_ids": [], "type_ids": [], "symbol_ids": []},
        },
        is_latest=True,
    )
    ParseResult.objects.create(
        card_version=version,
        raw_ocr_json={},
        normalized_fields_json={},
        confidence_json={},
    )
    for type_label in type_labels or []:
        type_key = type_label.lower().replace(" ", "-")
        type_row, _created = Type.objects.get_or_create(
            key=type_key,
            defaults={"label": type_label, "identifiers_json": []},
        )
        CardVersionType.objects.create(card_version=version, type=type_row)
    card.latest_version = version
    card.save(update_fields=["latest_version"])
    return card


def _build_mainboard_cards(total_unique: int = 15) -> list[Card]:
    return [_create_card(name=f"Mainboard Card {index}", is_hero=False) for index in range(total_unique)]


def _valid_entries(cards: Iterable[Card]) -> list[dict[str, object]]:
    return [{"card_id": card.id, "quantity": 4} for card in cards]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_excludes_private_decks() -> None:
    owner = _create_user("deck-public-owner", "password")
    hero = _create_card(name="Public Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()

    public_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Public Deck",
        description="Visible",
        is_public=True,
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Private Deck",
        description="Hidden",
        is_public=False,
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
    )

    response = Client(HTTP_HOST="localhost").get("/decks")

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == [public_deck.id]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_excludes_invalid_public_decks() -> None:
    owner = _create_user("deck-invalid-public-owner", "password")
    hero = _create_card(name="Draft Hero", is_hero=True)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Draft Deck",
        description=None,
        is_public=True,
        hero_card_id=hero.id,
        entries=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks")

    assert response.status_code == 200
    assert deck.id not in [row["id"] for row in response.json()]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_payload_includes_card_types() -> None:
    owner = _create_user("deck-types-owner", "password")
    hero = _create_card(name="Typed Hero", is_hero=True, type_labels=["Hero", "Mage"])
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Typed Deck",
        description=None,
        is_public=True,
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")

    assert response.status_code == 200
    assert [(row["key"], row["label"]) for row in response.json()["hero_card"]["types"]] == [
        ("hero", "Hero"),
        ("mage", "Mage"),
    ]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_detail_hides_private_decks_from_non_owners() -> None:
    owner = _create_user("deck-private-owner", "password")
    hero = _create_card(name="Private Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Private Deck",
        description=None,
        is_public=False,
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")

    assert response.status_code == 404


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_authenticated_owner_can_crud_decks() -> None:
    username = "deck-owner-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Owner Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/my/decks",
        data={
            "name": "Owner Deck",
            "description": "Owner description",
            "is_public": True,
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]

    list_response = client.get("/my/decks")
    detail_response = client.get(f"/my/decks/{deck_id}")
    patch_response = client.patch(
        f"/my/decks/{deck_id}",
        data={
            "name": "Owner Deck Updated",
            "description": "Updated description",
            "is_public": False,
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    delete_response = client.delete(
        f"/my/decks/{deck_id}",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Owner Deck Updated"
    assert patch_response.json()["is_public"] is False
    assert patch_response.json()["status"]["is_valid"] is True
    assert delete_response.status_code == 204
    assert Deck.objects.filter(id=deck_id).count() == 0


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_non_owner_cannot_update_or_delete_deck() -> None:
    owner = _create_user("deck-owner-locked", "password")
    other_user = _create_user("deck-other-locked", "password")
    hero = _create_card(name="Locked Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Locked Deck",
        description=None,
        is_public=True,
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, other_user.username, "password")

    patch_response = client.patch(
        f"/my/decks/{deck.id}",
        data={
            "name": "Nope",
            "description": None,
            "is_public": True,
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    delete_response = client.delete(
        f"/my/decks/{deck.id}",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_unauthenticated_users_are_blocked_from_my_decks() -> None:
    client = Client(HTTP_HOST="localhost")

    response = client.get("/my/decks")

    assert response.status_code in {401, 403}


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_create_rejects_non_hero_card_as_hero() -> None:
    username = "deck-invalid-hero-user"
    password = "password"
    _create_user(username, password)
    non_hero = _create_card(name="Not Hero", is_hero=False)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Invalid Hero Deck",
            "description": None,
            "is_public": False,
            "hero_card_id": non_hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Hero card must be marked as a hero."


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_create_allows_in_progress_drafts() -> None:
    username = "deck-invalid-count-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Count Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Draft Deck",
            "description": None,
            "is_public": True,
            "hero_card_id": hero.id,
            "entries": [{"card_id": card.id, "quantity": 3} for card in mainboard_cards],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["status"]["is_valid"] is False
    assert response.json()["status"]["label"] == "In Progress"
    assert response.json()["status"]["issues"] == ["Deck must contain exactly 60 mainboard cards."]


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_create_rejects_hero_in_mainboard() -> None:
    username = "deck-invalid-duplicate-hero-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Duplicate Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Invalid Duplicate Hero Deck",
            "description": None,
            "is_public": False,
            "hero_card_id": hero.id,
            "entries": [
                *_valid_entries(mainboard_cards),
                {"card_id": hero.id, "quantity": 4},
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Hero cards cannot appear in mainboard entries."


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_cards_list_can_filter_by_is_hero() -> None:
    hero_card = _create_card(name="Filter Hero", is_hero=True)
    non_hero_card = _create_card(name="Filter Non Hero", is_hero=False)
    client = Client(HTTP_HOST="localhost")

    hero_response = client.get("/cards", {"is_hero": "true"})
    non_hero_response = client.get("/cards", {"is_hero": "false"})

    assert hero_response.status_code == 200
    assert non_hero_response.status_code == 200
    assert hero_card.id in {row["id"] for row in hero_response.json()["results"]}
    assert non_hero_card.id not in {row["id"] for row in hero_response.json()["results"]}
    assert non_hero_card.id in {row["id"] for row in non_hero_response.json()["results"]}


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_latest_version_patch_can_toggle_is_hero() -> None:
    username = "deck-card-hero-toggle-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Toggle Hero Card", is_hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"is_hero": True},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    card.refresh_from_db()
    assert card.is_hero is True
    assert response.json()["is_hero"] is True

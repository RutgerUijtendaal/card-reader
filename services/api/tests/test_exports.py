from __future__ import annotations

import base64
import json

from django.test import Client

from card_reader_core.services.decks import DeckEntryInput, DeckService, DeckSideboardInput
from test_decks import _build_mainboard_cards, _create_card, _create_user, _login_and_get_csrf_token


def test_public_deck_tts_export_returns_base64_payload() -> None:
    owner = _create_user("tts-export-public-owner", "password")
    hero = _create_card(name="TTS Export Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Deck",
        description="Export me",
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    assert "tts-export-deck.tts.txt" in response["Content-Disposition"]
    payload = json.loads(base64.b64decode(response.content).decode("utf-8"))
    assert payload == {
        "schema": "card-reader.tts-deck.v1",
        "deck": {
            "name": "TTS Export Deck",
            "description": "Export me",
        },
        "hero": {
            "role": "hero",
            "quantity": 1,
            "name": hero.latest_version.name,
        },
        "cards": [
            {
                "role": "mainboard",
                "quantity": 4,
                "name": card.latest_version.name,
            }
            for card in mainboard_cards
        ],
    }
    assert len(payload["cards"]) == len(mainboard_cards)
    assert payload["cards"][0]["role"] == "mainboard"


def test_private_deck_tts_export_is_hidden_from_non_owner_but_visible_to_owner() -> None:
    owner = _create_user("tts-export-private-owner", "password")
    hero = _create_card(name="Private Export Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Private Export Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    public_response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    owner_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(owner_client, owner.username, "password")
    owner_response = owner_client.get(f"/decks/{deck.id}/exports/tts")

    assert public_response.status_code == 404
    assert owner_response.status_code == 200


def test_unlisted_deck_tts_export_is_visible_to_non_owner_by_link() -> None:
    owner = _create_user("tts-export-unlisted-owner", "password")
    hero = _create_card(name="Unlisted Export Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Unlisted Export Deck",
        description=None,
        visibility="unlisted",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200


def test_tts_export_omits_sideboard_entries_ignored_by_importer() -> None:
    owner = _create_user("tts-export-sideboard-owner", "password")
    hero = _create_card(name="TTS Export Sideboard Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="TTS Sideboard Card", is_hero=False)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Sideboard Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[
            DeckSideboardInput(
                name="Tech",
                entries=[DeckEntryInput(card_id=sideboard_card.id, quantity=6)],
            )
        ],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    payload = json.loads(base64.b64decode(response.content).decode("utf-8"))
    assert len(payload["cards"]) == len(mainboard_cards)
    assert "sideboards" not in payload
    assert "overall_total_cards" not in payload["deck"]


def test_tts_export_can_target_one_sideboard() -> None:
    owner = _create_user("tts-export-target-sideboard-owner", "password")
    hero = _create_card(name="TTS Export Target Sideboard Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="TTS Target Sideboard Card", is_hero=False)
    other_sideboard_card = _create_card(name="TTS Other Sideboard Card", is_hero=False)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Targeted Deck",
        description="Sideboard export",
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[
            DeckSideboardInput(
                name="Tech",
                entries=[DeckEntryInput(card_id=sideboard_card.id, quantity=6)],
            ),
            DeckSideboardInput(
                name="Practice",
                entries=[DeckEntryInput(card_id=other_sideboard_card.id, quantity=2)],
            ),
        ],
    )
    sideboard = next(sideboard for sideboard in deck.sideboards.all() if sideboard.name == "Tech")

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts?sideboard_id={sideboard.id}")

    assert response.status_code == 200
    assert "tts-export-targeted-deck-tech.tts.txt" in response["Content-Disposition"]
    payload = json.loads(base64.b64decode(response.content).decode("utf-8"))
    assert payload == {
        "schema": "card-reader.tts-deck.v1",
        "deck": {
            "name": "TTS Export Targeted Deck - Tech",
            "description": "Sideboard export",
        },
        "cards": [
            {
                "role": "sideboard",
                "quantity": 6,
                "name": sideboard_card.latest_version.name,
            }
        ],
    }
    assert "hero" not in payload


def test_tts_export_rejects_unknown_sideboard_id() -> None:
    owner = _create_user("tts-export-missing-sideboard-owner", "password")
    hero = _create_card(name="TTS Export Missing Sideboard Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Missing Sideboard Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts?sideboard_id=missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Sideboard not found"


def test_tts_export_preserves_saved_entry_order() -> None:
    owner = _create_user("tts-export-order-owner", "password")
    hero = _create_card(name="TTS Export Order Hero", is_hero=True)
    alpha_card = _create_card(name="Alpha TTS Card", is_hero=False)
    beta_card = _create_card(name="Beta TTS Card", is_hero=False)
    filler_cards = _build_mainboard_cards(total_unique=13)
    sideboard_alpha_card = _create_card(name="Alpha Sideboard TTS Card", is_hero=False)
    sideboard_beta_card = _create_card(name="Beta Sideboard TTS Card", is_hero=False)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Ordered Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=beta_card.id, quantity=1),
            DeckEntryInput(card_id=alpha_card.id, quantity=1),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in filler_cards],
        ],
        sideboards=[
            DeckSideboardInput(
                name="Tech",
                entries=[
                    DeckEntryInput(card_id=sideboard_beta_card.id, quantity=1),
                    DeckEntryInput(card_id=sideboard_alpha_card.id, quantity=1),
                ],
            )
        ],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    payload = json.loads(base64.b64decode(response.content).decode("utf-8"))
    assert [card["name"] for card in payload["cards"][:2]] == [
        beta_card.latest_version.name,
        alpha_card.latest_version.name,
    ]
    assert "sideboards" not in payload


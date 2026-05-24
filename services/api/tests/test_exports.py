from __future__ import annotations

import base64
import json

from django.test import Client, override_settings

from card_reader_core.services.decks import DeckEntryInput, DeckService
from test_decks import _build_mainboard_cards, _create_card, _create_user, _login_and_get_csrf_token


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_tts_export_returns_base64_payload() -> None:
    owner = _create_user("tts-export-public-owner", "password")
    hero = _create_card(name="TTS Export Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Deck",
        description="Export me",
        is_public=True,
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    assert "tts-export-deck.tts.txt" in response["Content-Disposition"]
    payload = json.loads(base64.b64decode(response.content).decode("utf-8"))
    assert payload["schema"] == "card-reader.tts-deck.v1"
    assert payload["deck"]["id"] == deck.id
    assert payload["deck"]["name"] == "TTS Export Deck"
    assert payload["hero"]["card_id"] == hero.id
    assert payload["hero"]["role"] == "hero"
    assert len(payload["cards"]) == len(mainboard_cards)
    assert payload["cards"][0]["role"] == "mainboard"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_private_deck_tts_export_is_hidden_from_non_owner_but_visible_to_owner() -> None:
    owner = _create_user("tts-export-private-owner", "password")
    hero = _create_card(name="Private Export Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Private Export Deck",
        description=None,
        is_public=False,
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
    )

    public_response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    owner_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(owner_client, owner.username, "password")
    owner_response = owner_client.get(f"/decks/{deck.id}/exports/tts")

    assert public_response.status_code == 404
    assert owner_response.status_code == 200

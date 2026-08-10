from __future__ import annotations

from collections.abc import Iterable
from itertools import count

from django.contrib.auth import get_user_model
from django.db import connection
from django.http import HttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext

from card_reader_core.models import (
    Card,
    CardRoleAssignment,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Deck,
    DeckCreation,
    DeckTag,
    DeckTagAssignment,
    DeckTagSuggestion,
    Keyword,
    ParseResult,
    Symbol,
    Tag,
    Template,
    Type,
)
from card_reader_core.repositories.cards import list_cards
from card_reader_core.config.settings import settings
from card_reader_core.storage import build_storage_relative_path
from card_reader_core.services.decks import (
    DeckConstraintEntry,
    DeckConstraintEvaluator,
    DeckEntryInput,
    DeckService,
    DeckSideboardInput,
    DeckUpdateInput,
)
from card_reader_core.services.deck_tags import DeckTagService

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


def _create_card(
    *,
    name: str,
    hero: bool,
    type_labels: list[str] | None = None,
    lifecycle_status: str = "active",
    deck_building_config: dict[str, object] | None = None,
) -> Card:
    template = _ensure_template()
    unique_name = f"{name} {next(_CARD_NAME_COUNTER)}"
    card = Card.objects.create(
        key=unique_name.lower().replace(" ", "-"),
        label=unique_name,
        lifecycle_status=lifecycle_status,
        deck_building_config_json=deck_building_config or {},
    )
    if hero:
        CardRoleAssignment.objects.create(card=card, role="hero")
    version = CardVersion.objects.create(
        card=card,
        version_number=1,
        template=template,
        image_hash=f"hash-{unique_name}",
        name=unique_name,
        type_line="Hero" if hero else "Follower",
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
                "type_line": "Hero" if hero else "Follower",
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


def _add_card_metadata(
    card: Card,
    *,
    keyword_labels: list[str] | None = None,
    tag_labels: list[str] | None = None,
    symbol_specs: list[tuple[str, str, str] | tuple[str, str, str, str]] | None = None,
) -> None:
    version = card.latest_version
    assert version is not None

    for keyword_label in keyword_labels or []:
        keyword_key = keyword_label.lower().replace(" ", "-")
        keyword, _created = Keyword.objects.get_or_create(
            key=keyword_key,
            defaults={"label": keyword_label, "identifiers_json": []},
        )
        CardVersionKeyword.objects.get_or_create(card_version=version, keyword=keyword)

    for tag_label in tag_labels or []:
        tag_key = tag_label.lower().replace(" ", "-")
        tag, _created = Tag.objects.get_or_create(
            key=tag_key,
            defaults={"label": tag_label, "identifiers_json": []},
        )
        CardVersionTag.objects.get_or_create(card_version=version, tag=tag)

    for symbol_spec in symbol_specs or []:
        symbol_key, symbol_label, text_token = symbol_spec[:3]
        symbol_type = symbol_spec[3] if len(symbol_spec) > 3 else "mana"
        symbol, _created = Symbol.objects.get_or_create(
            key=symbol_key,
            defaults={
                "label": symbol_label,
                "symbol_type": symbol_type,
                "detector_type": "template",
                "detection_config_json": {},
                "text_enrichment_json": {},
                "reference_assets_json": [],
                "text_token": text_token,
                "enabled": True,
            },
        )
        CardVersionSymbol.objects.get_or_create(card_version=version, symbol=symbol)


def _build_mainboard_cards(total_unique: int = 15) -> list[Card]:
    cards: list[Card] = []
    for index in range(total_unique):
        type_labels = ["Mana"] if index < 3 else None
        cards.append(_create_card(name=f"Mainboard Card {index}", hero=False, type_labels=type_labels))
    return cards


def _valid_entries(cards: Iterable[Card]) -> list[dict[str, object]]:
    return [{"card_id": card.id, "quantity": 4} for card in cards]


def _minimum_valid_entries(cards: Iterable[Card]) -> list[dict[str, object]]:
    return [{"card_id": card.id, "quantity": 4} for card in list(cards)[:10]]


def test_deck_rules_metadata_endpoint_returns_backend_owned_defaults() -> None:
    response = Client().get("/decks/rules")

    assert response.status_code == 200
    payload = response.json()
    assert payload["allowed_severities"] == ["hard", "soft"]
    assert payload["allowed_scopes"] == ["mainboard", "whole_deck"]
    assert payload["allowed_applications"] == ["deck", "self"]
    assert payload["default_config"] == {"overrides": {}}
    assert set(payload["supported_rule_ids"]) == {
        "mainboard_copy_limit",
        "mainboard_card_count",
        "mana_type_count",
        "legendary_copy_limit",
        "sideboard_entry_quantity",
    }
    assert payload["default_rules"]["mainboard_copy_limit"]["max"] == 4
    assert payload["default_rules"]["mainboard_copy_limit"]["severity"] == "hard"
    assert payload["default_rules"]["mana_type_count"]["min"] == 3
    assert payload["default_rules"]["legendary_copy_limit"]["severity"] == "soft"
    assert payload["example_config"]["overrides"]["mainboard_copy_limit"]["applies_to"] == "self"
    assert payload["example_config"]["overrides"]["mainboard_copy_limit"]["max"] == 6
    assert payload["example_config"]["overrides"]["legendary_copy_limit"]["applies_to"] == "deck"
    assert payload["example_config"]["overrides"]["legendary_copy_limit"]["scope"] == "whole_deck"


def test_public_deck_list_excludes_private_decks() -> None:
    owner = _create_user("deck-public-owner", "password")
    hero = _create_card(name="Public Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()

    public_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Public Deck",
        description="Visible",
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Private Deck",
        description="Hidden",
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Unlisted Deck",
        description="Share only",
        visibility="unlisted",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks")

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == [public_deck.id]


def test_public_deck_list_excludes_invalid_public_decks() -> None:
    owner = _create_user("deck-invalid-public-owner", "password")
    hero = _create_card(name="Draft Hero", hero=True)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Draft Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks")

    assert response.status_code == 200
    assert deck.id not in [row["id"] for row in response.json()]


def test_public_deck_list_excludes_decks_with_deprecated_cards_but_owner_can_view_warning() -> None:
    owner = _create_user("deck-deprecated-card-owner", "password")
    hero = _create_card(name="Deprecated Warning Hero", hero=True)
    deprecated_card = _create_card(
        name="Deprecated Mainboard Card",
        hero=False,
        lifecycle_status="deprecated",
        type_labels=["Mana"],
    )
    filler_cards = _build_mainboard_cards(total_unique=14)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Deprecated Card Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=deprecated_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in filler_cards],
        ],
        sideboards=[],
    )
    owner_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(owner_client, owner.username, "password")

    public_list_response = Client(HTTP_HOST="localhost").get("/decks")
    public_detail_response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")
    owner_detail_response = owner_client.get(f"/my/decks/{deck.id}")

    assert public_list_response.status_code == 200
    assert deck.id not in [row["id"] for row in public_list_response.json()]
    assert public_detail_response.status_code == 404
    assert owner_detail_response.status_code == 200
    status_payload = owner_detail_response.json()["status"]
    assert status_payload["is_valid"] is False
    assert status_payload["deprecated_card_count"] == 1
    assert status_payload["deprecated_card_ids"] == [deprecated_card.id]
    assert "Deck contains deprecated cards." in status_payload["issues"]


def test_public_deck_list_includes_valid_20_card_public_decks() -> None:
    owner = _create_user("deck-minimum-public-owner", "password")
    hero = _create_card(name="Minimum Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Minimum Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card["card_id"], quantity=int(card["quantity"])) for card in _minimum_valid_entries(mainboard_cards)],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks")

    assert response.status_code == 200
    assert deck.id in [row["id"] for row in response.json()]


def test_public_deck_summary_list_excludes_private_and_invalid_decks() -> None:
    owner = _create_user("deck-summary-public-owner", "password")
    hero = _create_card(name="Summary Public Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    public_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Summary Public Deck",
        description="Visible summary",
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Summary Public Private Deck",
        description="Hidden summary",
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    invalid_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Summary Public Invalid Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks", {"view": "summary", "q": "Summary Public"})

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == [public_deck.id]
    assert invalid_deck.id not in [row["id"] for row in payload]
    summary = payload[0]
    assert summary["mainboard"] == {"total_cards": 60, "unique_cards": 15}
    assert summary["sideboard_count"] == 0
    assert "entries" not in summary["mainboard"]
    assert "sideboards" not in summary
    assert "deck_building_rules" not in summary

    page_response = Client(HTTP_HOST="localhost").get(
        "/decks",
        {"view": "summary", "q": "Summary Public", "page": 1, "page_size": 10},
    )
    assert page_response.status_code == 200
    page_payload = page_response.json()
    assert isinstance(page_payload["snapshot_at"], str)
    assert page_payload == {
        "count": 1,
        "next_page": None,
        "next_cursor": None,
        "previous_page": None,
        "page": 1,
        "page_size": 10,
        "snapshot_at": page_payload["snapshot_at"],
        "results": payload,
    }


def test_owner_deck_summary_list_returns_all_owned_visibility_states() -> None:
    owner = _create_user("deck-summary-owner-user", "password")
    other_owner = _create_user("deck-summary-other-user", "password")
    hero = _create_card(name="Summary Owner Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(client, owner.username, "password")

    owned_decks = [
        DeckService().create_owner_deck(
            owner_id=str(owner.id),
            name=f"Summary Owned {visibility}",
            description=None,
            visibility=visibility,
            hero_card_id=hero.id,
            entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
            sideboards=[],
        )
        for visibility in ("private", "unlisted", "public")
    ]
    DeckService().create_owner_deck(
        owner_id=str(other_owner.id),
        name="Summary Other Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = client.get("/my/decks", {"view": "summary"})

    assert response.status_code == 200
    payload_ids = {row["id"] for row in response.json()}
    assert payload_ids == {deck.id for deck in owned_decks}

    page_response = client.get("/my/decks", {"view": "summary", "page": 2, "page_size": 2})
    assert page_response.status_code == 200
    page_payload = page_response.json()
    assert page_payload["count"] == 3
    assert page_payload["page"] == 2
    assert page_payload["page_size"] == 2
    assert isinstance(page_payload["snapshot_at"], str)
    assert page_payload["previous_page"] == 1
    assert page_payload["next_page"] is None
    assert len(page_payload["results"]) == 1
    assert page_payload["results"][0]["id"] in {deck.id for deck in owned_decks}

    out_of_range_response = client.get(
        "/my/decks",
        {"view": "summary", "page": 99, "page_size": 2},
    )
    assert out_of_range_response.status_code == 200
    out_of_range_payload = out_of_range_response.json()
    assert out_of_range_payload["count"] == 3
    assert out_of_range_payload["page"] == 2
    assert out_of_range_payload["previous_page"] == 1
    assert out_of_range_payload["next_page"] is None
    assert len(out_of_range_payload["results"]) == 1

    stable_first_response = client.get(
        "/my/decks",
        {"view": "summary", "page": 1, "page_size": 2},
    )
    assert stable_first_response.status_code == 200
    stable_first_payload = stable_first_response.json()
    stable_first_ids = {row["id"] for row in stable_first_payload["results"]}
    remaining_deck = next(deck for deck in owned_decks if deck.id not in stable_first_ids)
    DeckService().update_deck(
        deck_id=remaining_deck.id,
        updates=DeckUpdateInput(difficulty="easy", update_difficulty=True),
    )

    stable_second_response = client.get(
        "/my/decks",
        {
            "view": "summary",
            "page": 2,
            "page_size": 2,
            "snapshot_at": stable_first_payload["snapshot_at"],
            "cursor_created_at": stable_first_payload["next_cursor"]["created_at"],
            "cursor_id": stable_first_payload["next_cursor"]["id"],
        },
    )
    assert stable_second_response.status_code == 200
    stable_second_payload = stable_second_response.json()
    stable_second_ids = {row["id"] for row in stable_second_payload["results"]}
    assert stable_first_ids | stable_second_ids == {deck.id for deck in owned_decks}

    newer_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Summary Owned After Snapshot",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    snapshot_response = client.get(
        "/my/decks",
        {
            "view": "summary",
            "page": 1,
            "page_size": 10,
            "snapshot_at": stable_first_payload["snapshot_at"],
        },
    )
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()
    assert snapshot_payload["count"] == 3
    assert newer_deck.id not in {row["id"] for row in snapshot_payload["results"]}

    snapshot_only_response = client.get(
        "/my/decks",
        {
            "view": "summary",
            "snapshot_at": stable_first_payload["snapshot_at"],
        },
    )
    assert snapshot_only_response.status_code == 200
    snapshot_only_payload = snapshot_only_response.json()
    assert snapshot_only_payload["page"] == 1
    assert snapshot_only_payload["page_size"] == 10
    assert snapshot_only_payload["snapshot_at"] == stable_first_payload["snapshot_at"]

    consumed_deck_id = next(iter(stable_first_ids))
    assert DeckService().delete_owner_deck(deck_id=consumed_deck_id, owner_id=str(owner.id))
    after_delete_response = client.get(
        "/my/decks",
        {
            "view": "summary",
            "page": 2,
            "page_size": 2,
            "snapshot_at": stable_first_payload["snapshot_at"],
            "cursor_created_at": stable_first_payload["next_cursor"]["created_at"],
            "cursor_id": stable_first_payload["next_cursor"]["id"],
        },
    )
    assert after_delete_response.status_code == 200
    after_delete_ids = {row["id"] for row in after_delete_response.json()["results"]}
    assert after_delete_ids == {deck.id for deck in owned_decks} - stable_first_ids


def test_deck_summary_search_matches_overview_fields_without_leaking_private_decks() -> None:
    owner = _create_user("deck-summary-search-owner", "password")
    other_owner = _create_user("deck-summary-search-other", "password")
    deck_name_hero = _create_card(name="Neutral Summary Hero", hero=True)
    hero_match = _create_card(name="Summary Search Hero", hero=True)
    mainboard_match = _create_card(name="Summary Search Blade", hero=False, type_labels=["Mana"])
    sideboard_match = _create_card(name="Summary Search Trap", hero=False)
    mainboard_cards = _build_mainboard_cards(total_unique=14)

    name_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Summary Search Deck Name",
        description=None,
        visibility="public",
        hero_card_id=deck_name_hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )
    hero_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Hero Query Deck",
        description=None,
        visibility="public",
        hero_card_id=hero_match.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )
    card_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Card Query Deck",
        description=None,
        visibility="public",
        hero_card_id=deck_name_hero.id,
        entries=[
            DeckEntryInput(card_id=mainboard_match.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        ],
        sideboards=[],
    )
    sideboard_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Sideboard Query Deck",
        description=None,
        visibility="public",
        hero_card_id=deck_name_hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[DeckSideboardInput(name="Flex", entries=[DeckEntryInput(card_id=sideboard_match.id, quantity=1)])],
    )
    author_deck = DeckService().create_owner_deck(
        owner_id=str(other_owner.id),
        name="Author Query Deck",
        description=None,
        visibility="public",
        hero_card_id=deck_name_hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )
    private_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Summary Private Search Deck",
        description=None,
        visibility="private",
        hero_card_id=deck_name_hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )

    client = Client(HTTP_HOST="localhost")

    assert [row["id"] for row in client.get("/decks", {"view": "summary", "q": "Deck Name"}).json()] == [name_deck.id]
    assert [row["id"] for row in client.get("/decks", {"view": "summary", "q": "Search Hero"}).json()] == [hero_deck.id]
    assert [row["id"] for row in client.get("/decks", {"view": "summary", "q": "Search Blade"}).json()] == [card_deck.id]
    assert [row["id"] for row in client.get("/decks", {"view": "summary", "q": "Search Trap"}).json()] == [sideboard_deck.id]
    assert [row["id"] for row in client.get("/decks", {"view": "summary", "q": other_owner.username}).json()] == [author_deck.id]
    assert private_deck.id not in [
        row["id"] for row in client.get("/decks", {"view": "summary", "q": "Private Search"}).json()
    ]


def test_deck_summary_list_query_count_stays_bounded() -> None:
    owner = _create_user("deck-summary-query-owner", "password")
    hero = _create_card(name="Summary Query Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    for index in range(4):
        DeckService().create_owner_deck(
            owner_id=str(owner.id),
            name=f"Summary Query Deck {index}",
            description=None,
            visibility="public",
            hero_card_id=hero.id,
            entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
            sideboards=[],
        )

    with CaptureQueriesContext(connection) as queries:
        response = Client(HTTP_HOST="localhost").get("/decks", {"view": "summary", "q": "Summary Query Deck"})

    assert response.status_code == 200
    assert len(response.json()) == 4
    assert len(queries.captured_queries) <= 20


def test_public_deck_list_filters_by_hero_name() -> None:
    owner = _create_user("deck-filter-hero-owner", "password")
    target_hero = _create_card(name="Aurora Captain", hero=True)
    other_hero = _create_card(name="Shadow Caller", hero=True)
    mainboard_cards = _build_mainboard_cards()

    target_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Aurora Deck",
        description=None,
        visibility="public",
        hero_card_id=target_hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Shadow Deck",
        description=None,
        visibility="public",
        hero_card_id=other_hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks", {"hero_q": "Aurora"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [target_deck.id]


def test_public_deck_list_filters_by_author_username() -> None:
    target_owner = _create_user("deck-author-target", "password")
    other_owner = _create_user("deck-author-other", "password")
    hero = _create_card(name="Author Filter Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()

    target_deck = DeckService().create_owner_deck(
        owner_id=str(target_owner.id),
        name="Target Author Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    other_deck = DeckService().create_owner_deck(
        owner_id=str(other_owner.id),
        name="Other Author Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks", {"author_q": "target"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [target_deck.id]
    assert other_deck.id not in [row["id"] for row in response.json()]


def test_public_deck_list_filters_by_mainboard_card_name() -> None:
    owner = _create_user("deck-filter-mainboard-owner", "password")
    hero = _create_card(name="Mainboard Hero", hero=True)
    featured_card = _create_card(name="Sun Spear", hero=False)
    filler_cards = _build_mainboard_cards(total_unique=14)

    target_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Sun Spear Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=featured_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in filler_cards],
        ],
        sideboards=[],
    )
    other_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Other Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks", {"card_q": "Sun Spear"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [target_deck.id]
    assert other_deck.id not in [row["id"] for row in response.json()]


def test_public_deck_list_filters_by_sideboard_card_name() -> None:
    owner = _create_user("deck-filter-sideboard-owner", "password")
    hero = _create_card(name="Sideboard Filter Hero", hero=True)
    sideboard_card = _create_card(name="Moon Trap", hero=False)
    mainboard_cards = _build_mainboard_cards()

    target_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Moon Trap Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[
            DeckSideboardInput(
                name="Flex",
                entries=[DeckEntryInput(card_id=sideboard_card.id, quantity=2)],
            )
        ],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="No Match Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks", {"card_q": "Moon Trap"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [target_deck.id]


def test_public_deck_list_combines_hero_and_card_filters_with_and() -> None:
    owner = _create_user("deck-filter-and-owner", "password")
    matching_hero = _create_card(name="Ember Warden", hero=True)
    non_matching_hero = _create_card(name="Frost Sage", hero=True)
    featured_card = _create_card(name="Solar Flare", hero=False)
    filler_cards = _build_mainboard_cards(total_unique=14)

    target_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Matching Deck",
        description=None,
        visibility="public",
        hero_card_id=matching_hero.id,
        entries=[
            DeckEntryInput(card_id=featured_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in filler_cards],
        ],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Hero Only Deck",
        description=None,
        visibility="public",
        hero_card_id=matching_hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Card Only Deck",
        description=None,
        visibility="public",
        hero_card_id=non_matching_hero.id,
        entries=[
            DeckEntryInput(card_id=featured_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks", {"hero_q": "Ember", "card_q": "Solar"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [target_deck.id]


def test_public_deck_list_filters_by_affinity_symbols_with_any_match() -> None:
    owner = _create_user("deck-filter-affinity-any-owner", "password")
    hero = _create_card(name="Affinity Any Hero", hero=True)
    fire_card = _create_card(name="Firecard", hero=False)
    water_card = _create_card(name="Watercard", hero=False)
    _add_card_metadata(fire_card, symbol_specs=[("aff-fire", "Fire Affinity", "{AF}", "affinity")])
    _add_card_metadata(water_card, symbol_specs=[("aff-water", "Water Affinity", "{AW}", "affinity")])
    fire_symbol_id = Symbol.objects.get(key="aff-fire").id
    water_symbol_id = Symbol.objects.get(key="aff-water").id

    fire_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Fire Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=fire_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )
    water_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Water Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=water_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(
        "/decks",
        {"affinity_symbol_ids": [fire_symbol_id, water_symbol_id], "affinity_symbol_match": "any"},
    )

    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {fire_deck.id, water_deck.id}


def test_public_deck_list_filters_by_affinity_symbols_with_all_match() -> None:
    owner = _create_user("deck-filter-affinity-all-owner", "password")
    hero = _create_card(name="Affinity All Hero", hero=True)
    dual_card = _create_card(name="Dual Affinity Card", hero=False)
    fire_only_card = _create_card(name="Fire Only Card", hero=False)
    _add_card_metadata(
        dual_card,
        symbol_specs=[
            ("aff-fire-all", "Fire Affinity", "{AF}", "affinity"),
            ("aff-water-all", "Water Affinity", "{AW}", "affinity"),
        ],
    )
    _add_card_metadata(fire_only_card, symbol_specs=[("aff-fire-all", "Fire Affinity", "{AF}", "affinity")])
    fire_symbol_id = Symbol.objects.get(key="aff-fire-all").id
    water_symbol_id = Symbol.objects.get(key="aff-water-all").id

    dual_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Dual Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=dual_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Fire Only Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=fire_only_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(
        "/decks",
        {"affinity_symbol_ids": [fire_symbol_id, water_symbol_id], "affinity_symbol_match": "all"},
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [dual_deck.id]


def test_public_deck_list_filters_by_affinity_symbol_exclusions() -> None:
    owner = _create_user("deck-filter-affinity-exclude-owner", "password")
    hero = _create_card(name="Affinity Exclude Hero", hero=True)
    fire_card = _create_card(name="Exclude Fire Card", hero=False)
    water_card = _create_card(name="Exclude Water Card", hero=False)
    dual_card = _create_card(name="Exclude Dual Card", hero=False)
    _add_card_metadata(fire_card, symbol_specs=[("aff-fire-exclude", "Fire Affinity", "{AF}", "affinity")])
    _add_card_metadata(water_card, symbol_specs=[("aff-water-exclude", "Water Affinity", "{AW}", "affinity")])
    _add_card_metadata(
        dual_card,
        symbol_specs=[
            ("aff-fire-exclude", "Fire Affinity", "{AF}", "affinity"),
            ("aff-water-exclude", "Water Affinity", "{AW}", "affinity"),
        ],
    )
    fire_symbol_id = Symbol.objects.get(key="aff-fire-exclude").id
    water_symbol_id = Symbol.objects.get(key="aff-water-exclude").id

    fire_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Exclude Fire Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=fire_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Exclude Water Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=water_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Exclude Dual Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=dual_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(
        "/decks",
        {
            "affinity_symbol_ids": [fire_symbol_id, water_symbol_id],
            "affinity_symbol_match": "any",
            "affinity_symbol_exclude_ids": [water_symbol_id],
        },
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [fire_deck.id]


def test_public_deck_list_filters_still_exclude_private_and_invalid_decks() -> None:
    owner = _create_user("deck-filter-visibility-owner", "password")
    target_hero = _create_card(name="Visible Filter Hero", hero=True)
    private_hero = _create_card(name="Hidden Filter Hero", hero=True)
    invalid_hero = _create_card(name="Draft Filter Hero", hero=True)
    featured_card = _create_card(name="Comet Blade", hero=False)
    filler_cards = _build_mainboard_cards(total_unique=14)

    public_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Visible Filter Deck",
        description=None,
        visibility="public",
        hero_card_id=target_hero.id,
        entries=[
            DeckEntryInput(card_id=featured_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in filler_cards],
        ],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Private Filter Deck",
        description=None,
        visibility="private",
        hero_card_id=private_hero.id,
        entries=[
            DeckEntryInput(card_id=featured_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Invalid Filter Deck",
        description=None,
        visibility="public",
        hero_card_id=invalid_hero.id,
        entries=[DeckEntryInput(card_id=featured_card.id, quantity=1)],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks", {"card_q": "Comet Blade"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [public_deck.id]


def test_deck_payload_includes_card_types() -> None:
    owner = _create_user("deck-types-owner", "password")
    hero = _create_card(name="Typed Hero", hero=True, type_labels=["Hero", "Mage"])
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Typed Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")

    assert response.status_code == 200
    assert [(row["key"], row["label"]) for row in response.json()["hero_card"]["types"]] == [
        ("hero", "Hero"),
        ("mage", "Mage"),
    ]


def test_deck_payload_includes_tooltip_metadata() -> None:
    owner = _create_user("deck-tooltip-owner", "password")
    hero = _create_card(name="Tooltip Hero", hero=True)
    card = _create_card(name="Tooltip Card", hero=False, type_labels=["Equipment", "Amulet"])
    _add_card_metadata(
        card,
        keyword_labels=["Gain"],
        tag_labels=["Fire"],
        symbol_specs=[("mana-fire", "Mana - Fire", "{fire}")],
    )

    filler_cards = _build_mainboard_cards(total_unique=14)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Tooltip Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=card.id, quantity=4),
            *[DeckEntryInput(card_id=filler.id, quantity=4) for filler in filler_cards],
        ],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")

    assert response.status_code == 200
    payload_card = next(
        row["card"]
        for row in response.json()["mainboard"]["entries"]
        if row["card"]["id"] == card.id
    )
    assert payload_card["template_id"] == "deck-test-template"
    assert payload_card["version_number"] == 1
    assert payload_card["type_line"] == "Follower"
    assert payload_card["keywords"] == ["Gain"]
    assert [(row["key"], row["label"]) for row in payload_card["tags"]] == [("fire", "Fire")]
    assert [(row["key"], row["label"]) for row in payload_card["types"]] == [
        ("amulet", "Amulet"),
        ("equipment", "Equipment"),
    ]
    assert [(row["key"], row["label"], row["text_token"]) for row in payload_card["symbols"]] == [
        ("mana-fire", "Mana - Fire", "{fire}")
    ]


def test_deck_payload_uses_immutable_card_image_urls() -> None:
    owner = _create_user("deck-image-owner", "password")
    hero = _create_card(name="Image Hero", hero=True)
    version = hero.latest_version
    assert version is not None
    image_name = f"deck-image-{version.id}.png"
    image_path = settings.image_store_dir / image_name
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"deck-image")
    CardVersionImage.objects.create(
        card_version=version,
        source_file=build_storage_relative_path("images", image_name),
        stored_path=build_storage_relative_path("images", image_name),
        checksum=f"checksum-{version.id}",
    )
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Image Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")

    assert response.status_code == 200
    assert response.json()["hero_card"]["image_url"] == f"/card-images/images/{image_name}"


def test_deck_summary_uses_first_existing_prefetched_hero_image() -> None:
    owner = _create_user("deck-summary-image-owner", "password")
    hero = _create_card(name="Summary Image Hero", hero=True)
    version = hero.latest_version
    assert version is not None
    valid_image_name = f"deck-summary-valid-image-{version.id}.png"
    valid_image_path = settings.image_store_dir / valid_image_name
    valid_image_path.parent.mkdir(parents=True, exist_ok=True)
    valid_image_path.write_bytes(b"deck-summary-image")
    CardVersionImage.objects.create(
        card_version=version,
        source_file=build_storage_relative_path("images", valid_image_name),
        stored_path=build_storage_relative_path("images", valid_image_name),
        checksum=f"summary-valid-checksum-{version.id}",
    )
    CardVersionImage.objects.create(
        card_version=version,
        source_file=build_storage_relative_path("images", f"deck-summary-missing-source-{version.id}.png"),
        stored_path=build_storage_relative_path("images", f"deck-summary-missing-stored-{version.id}.png"),
        checksum=f"summary-missing-checksum-{version.id}",
    )
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Summary Image Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get("/decks", {"view": "summary", "q": "Summary Image Deck"})

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == [deck.id]
    assert payload[0]["hero_card"]["image_url"] == f"/card-images/images/{valid_image_name}"


def test_public_deck_detail_hides_private_decks_from_non_owners() -> None:
    owner = _create_user("deck-private-owner", "password")
    hero = _create_card(name="Private Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Private Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")

    assert response.status_code == 404


def test_public_deck_detail_allows_unlisted_decks_for_guests() -> None:
    owner = _create_user("deck-unlisted-owner", "password")
    hero = _create_card(name="Unlisted Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Unlisted Deck",
        description="Share me",
        visibility="unlisted",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")

    assert response.status_code == 200
    assert response.json()["visibility"] == "unlisted"


def test_authenticated_owner_can_crud_decks() -> None:
    username = "deck-owner-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Owner Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/my/decks",
        data={
            "name": "Owner Deck",
            "description": "Owner description",
            "visibility": "unlisted",
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
            "visibility": "public",
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
    assert create_response.json()["visibility"] == "unlisted"
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Owner Deck Updated"
    assert patch_response.json()["visibility"] == "public"
    assert patch_response.json()["status"]["is_valid"] is True
    assert delete_response.status_code == 204
    assert Deck.objects.filter(id=deck_id).count() == 0


def test_deck_long_description_round_trips_normalizes_and_stays_out_of_summaries() -> None:
    username = "deck-long-description-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Long Description Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/my/decks",
        data={
            "name": "Long Description Deck",
            "description": "Concise summary",
            "long_description": "  Opening plan\r\n\r\nSideboard notes\rFinal note  ",
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]
    expected_description = "Opening plan\n\nSideboard notes\nFinal note"
    assert create_response.json()["long_description"] == expected_description
    assert Deck.objects.get(id=deck_id).long_description == expected_description

    detail_response = client.get(f"/my/decks/{deck_id}")
    summary_response = client.get("/my/decks", {"view": "summary"})

    assert detail_response.status_code == 200
    assert detail_response.json()["long_description"] == expected_description
    assert summary_response.status_code == 200
    summary = next(row for row in summary_response.json() if row["id"] == deck_id)
    assert "long_description" not in summary


def test_deck_patch_preserves_and_clears_long_description() -> None:
    username = "deck-long-description-patch-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Long Description Patch Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)
    create_response = client.post(
        "/my/decks",
        data={
            "name": "Long Description Patch Deck",
            "long_description": "Keep this\n\nText",
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]

    preserve_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"name": "Renamed Deck"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    null_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"long_description": None},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    restore_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"long_description": "Restored"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    blank_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"long_description": " \r\n\t "},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert preserve_response.status_code == 200
    assert preserve_response.json()["long_description"] == "Keep this\n\nText"
    assert null_response.status_code == 200
    assert null_response.json()["long_description"] is None
    assert restore_response.status_code == 200
    assert restore_response.json()["long_description"] == "Restored"
    assert blank_response.status_code == 200
    assert blank_response.json()["long_description"] is None
    assert Deck.objects.get(id=deck_id).long_description is None


def test_deck_difficulty_round_trips_in_full_and_summary_payloads() -> None:
    username = "deck-difficulty-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Difficulty Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/my/decks",
        data={
            "name": "Difficult Deck",
            "difficulty": "hard",
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]
    assert create_response.json()["difficulty"] == "hard"
    assert Deck.objects.get(id=deck_id).difficulty == "hard"

    detail_response = client.get(f"/my/decks/{deck_id}")
    summary_response = client.get("/my/decks", {"view": "summary"})

    assert detail_response.status_code == 200
    assert detail_response.json()["difficulty"] == "hard"
    assert summary_response.status_code == 200
    summary = next(row for row in summary_response.json() if row["id"] == deck_id)
    assert summary["difficulty"] == "hard"

    invalid_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"difficulty": "expert"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert invalid_response.status_code == 400
    assert Deck.objects.get(id=deck_id).difficulty == "hard"


def test_deck_patch_preserves_and_clears_difficulty() -> None:
    username = "deck-difficulty-patch-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Difficulty Patch Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)
    create_response = client.post(
        "/my/decks",
        data={
            "name": "Difficulty Patch Deck",
            "difficulty": "medium",
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]

    preserve_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"name": "Renamed Difficulty Deck"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    clear_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"difficulty": None},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert preserve_response.status_code == 200
    assert preserve_response.json()["difficulty"] == "medium"
    assert clear_response.status_code == 200
    assert clear_response.json()["difficulty"] is None
    assert Deck.objects.get(id=deck_id).difficulty is None


def test_owner_deck_list_filters_owned_decks_by_card_name_without_leaking_other_users_decks() -> None:
    owner = _create_user("deck-owner-filter-user", "password")
    other_owner = _create_user("deck-owner-filter-other-user", "password")
    hero = _create_card(name="Owner Filter Hero", hero=True)
    featured_card = _create_card(name="Owner Filter Blade", hero=False)
    filler_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(client, owner.username, "password")

    matching_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Owned Matching Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=featured_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in filler_cards],
        ],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Owned Nonmatching Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )
    other_user_deck = DeckService().create_owner_deck(
        owner_id=str(other_owner.id),
        name="Other User Matching Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=featured_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )

    response = client.get("/my/decks", {"card_q": "Owner Filter Blade"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [matching_deck.id]
    assert other_user_deck.id not in [row["id"] for row in response.json()]


def test_owner_deck_list_ignores_public_author_filter() -> None:
    owner = _create_user("deck-owner-author-filter-user", "password")
    other_owner = _create_user("deck-owner-author-filter-other", "password")
    hero = _create_card(name="Owner Author Filter Hero", hero=True)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(client, owner.username, "password")

    owned_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Owned Author Filter Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )
    other_user_deck = DeckService().create_owner_deck(
        owner_id=str(other_owner.id),
        name="Other User Author Filter Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards()],
        sideboards=[],
    )

    response = client.get("/my/decks", {"author_q": other_owner.username})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [owned_deck.id]
    assert other_user_deck.id not in [row["id"] for row in response.json()]


def test_owner_deck_list_filters_owned_decks_by_affinity_symbol() -> None:
    owner = _create_user("deck-owner-affinity-filter-user", "password")
    hero = _create_card(name="Owner Affinity Hero", hero=True)
    fire_card = _create_card(name="Owner Fire Card", hero=False)
    water_card = _create_card(name="Owner Water Card", hero=False)
    _add_card_metadata(fire_card, symbol_specs=[("owner-aff-fire", "Owner Fire Affinity", "{OF}", "affinity")])
    _add_card_metadata(water_card, symbol_specs=[("owner-aff-water", "Owner Water Affinity", "{OW}", "affinity")])
    fire_symbol_id = Symbol.objects.get(key="owner-aff-fire").id
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(client, owner.username, "password")

    fire_deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Owned Fire Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=fire_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Owned Water Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[
            DeckEntryInput(card_id=water_card.id, quantity=4),
            *[DeckEntryInput(card_id=card.id, quantity=4) for card in _build_mainboard_cards(total_unique=14)],
        ],
        sideboards=[],
    )

    response = client.get(
        "/my/decks",
        {"affinity_symbol_ids": [fire_symbol_id], "affinity_symbol_match": "any"},
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [fire_deck.id]


def test_deck_payload_includes_sideboards_and_aggregate_totals() -> None:
    owner = _create_user("deck-sideboard-owner", "password")
    hero = _create_card(name="Sideboard Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Sideboard Card", hero=False)
    extra_sideboard_card = _create_card(name="Second Sideboard Card", hero=False)

    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Sideboard Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[
            DeckSideboardInput(
                name="Matchups",
                entries=[
                    DeckEntryInput(card_id=sideboard_card.id, quantity=7),
                    DeckEntryInput(card_id=mainboard_cards[0].id, quantity=2),
                ],
            ),
            DeckSideboardInput(
                name="Control",
                entries=[
                    DeckEntryInput(card_id=extra_sideboard_card.id, quantity=3),
                ],
            ),
        ],
    )

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"] == {
        "overall_total_cards": 72,
        "overall_unique_cards": 17,
        "mainboard_total_cards": 60,
        "mainboard_unique_cards": 15,
    }
    assert sorted((sideboard["name"], sideboard["total_cards"]) for sideboard in payload["sideboards"]) == [
        ("Control", 3),
        ("Matchups", 9),
    ]


def test_authenticated_owner_can_create_deck_with_sideboards() -> None:
    username = "deck-sideboard-crud-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard CRUD Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="CRUD Sideboard Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Owner Sideboard Deck",
            "description": "Has sideboards",
            "visibility": "public",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
            "sideboards": [
                {
                    "name": "Flex",
                    "entries": [
                        {"card_id": sideboard_card.id, "quantity": 9},
                        {"card_id": mainboard_cards[0].id, "quantity": 1},
                    ],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["sideboards"][0]["name"] == "Flex"
    assert payload["sideboards"][0]["total_cards"] == 10
    assert payload["totals"]["overall_total_cards"] == 70
    assert payload["status"]["is_valid"] is True


def test_deck_create_is_idempotent_per_owner_and_creation_key() -> None:
    username = "deck-idempotency-user"
    password = "password"
    owner = _create_user(username, password)
    hero = _create_card(name="Idempotency Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)
    creation_key = "7cb8ed4d-83ca-46c2-9b76-b33cc89188de"
    payload = {
        "name": "Idempotent Deck",
        "description": None,
        "visibility": "private",
        "hero_card_id": hero.id,
        "entries": _valid_entries(mainboard_cards),
        "sideboards": [],
    }

    first_response = client.post(
        "/my/decks",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
        HTTP_IDEMPOTENCY_KEY=creation_key,
    )
    replay_response = client.post(
        "/my/decks",
        data={"name": "invalid replay body"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
        HTTP_IDEMPOTENCY_KEY=creation_key,
    )

    assert first_response.status_code == 201
    assert replay_response.status_code == 200
    assert replay_response.json()["id"] == first_response.json()["id"]
    assert "client_creation_id" not in first_response.json()
    assert "client_creation_id" not in replay_response.json()
    assert Deck.objects.filter(owner=owner, client_creation_id=creation_key).count() == 1
    assert DeckCreation.objects.filter(owner=owner, client_creation_id=creation_key).count() == 1


def test_deck_create_replay_rejects_newly_restricted_cards_without_returning_card_data() -> None:
    username = "deck-idempotency-reclassified-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Idempotency Reclassified Hero", hero=True)
    reclassified = _create_card(name="Idempotency Secret Event", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)
    creation_key = "bf6cbe1c-ae32-4d2f-a7a8-b5f39175c5df"
    payload = {
        "name": "Idempotency Reclassified Deck",
        "description": None,
        "visibility": "private",
        "hero_card_id": hero.id,
        "entries": [{"card_id": reclassified.id, "quantity": 1}],
        "sideboards": [],
    }
    create_response = client.post(
        "/my/decks",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
        HTTP_IDEMPOTENCY_KEY=creation_key,
    )
    assert create_response.status_code == 201
    reclassified.card_pool = "game_master"
    reclassified.save(update_fields=["card_pool"])

    replay_response = client.post(
        "/my/decks",
        data={"name": "ignored replay body"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
        HTTP_IDEMPOTENCY_KEY=creation_key,
    )
    lookup_response = client.get(f"/my/decks/by-creation-key/{creation_key}")

    assert replay_response.status_code == 409
    assert lookup_response.status_code == 409
    assert replay_response.json() == {
        "detail": "The deck created by this key is no longer eligible for replay."
    }
    assert reclassified.id not in replay_response.content.decode()
    assert reclassified.label not in replay_response.content.decode()


def test_deck_creation_key_is_owner_scoped_and_lookup_is_private() -> None:
    creation_key = "b08b9444-9b79-4878-aef2-38bbf357578f"
    first_username = "deck-idempotency-first-user"
    second_username = "deck-idempotency-second-user"
    password = "password"
    _create_user(first_username, password)
    _create_user(second_username, password)
    hero = _create_card(name="Scoped Idempotency Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    payload = {
        "name": "Scoped Idempotency Deck",
        "description": None,
        "visibility": "private",
        "hero_card_id": hero.id,
        "entries": _valid_entries(mainboard_cards),
        "sideboards": [],
    }
    first_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    first_csrf = _login_and_get_csrf_token(first_client, first_username, password)
    second_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    second_csrf = _login_and_get_csrf_token(second_client, second_username, password)

    first_create = first_client.post(
        "/my/decks",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=first_csrf,
        HTTP_IDEMPOTENCY_KEY=creation_key,
    )
    missing_lookup = second_client.get(f"/my/decks/by-creation-key/{creation_key}")
    second_create = second_client.post(
        "/my/decks",
        data={**payload, "name": "Other Owner Deck"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=second_csrf,
        HTTP_IDEMPOTENCY_KEY=creation_key,
    )
    first_lookup = first_client.get(f"/my/decks/by-creation-key/{creation_key}")
    anonymous_lookup = Client(HTTP_HOST="localhost").get(
        f"/my/decks/by-creation-key/{creation_key}"
    )

    assert first_create.status_code == 201
    assert missing_lookup.status_code == 404
    assert second_create.status_code == 201
    assert second_create.json()["id"] != first_create.json()["id"]
    assert first_lookup.status_code == 200
    assert first_lookup.json()["id"] == first_create.json()["id"]
    assert anonymous_lookup.status_code == 403


def test_deleted_deck_keeps_creation_key_as_a_tombstone() -> None:
    username = "deck-idempotency-deleted-user"
    password = "password"
    owner = _create_user(username, password)
    hero = _create_card(name="Deleted Idempotency Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)
    creation_key = "503055a8-26e0-440d-a094-f90b4b9bb788"
    payload = {
        "name": "Deleted Idempotency Deck",
        "description": None,
        "visibility": "private",
        "hero_card_id": hero.id,
        "entries": _valid_entries(mainboard_cards),
        "sideboards": [],
    }

    create_response = client.post(
        "/my/decks",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
        HTTP_IDEMPOTENCY_KEY=creation_key,
    )
    deck_id = create_response.json()["id"]
    delete_response = client.delete(
        f"/my/decks/{deck_id}",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    lookup_response = client.get(f"/my/decks/by-creation-key/{creation_key}")
    retry_response = client.post(
        "/my/decks",
        data=payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
        HTTP_IDEMPOTENCY_KEY=creation_key,
    )

    assert create_response.status_code == 201
    assert delete_response.status_code == 204
    assert lookup_response.status_code == 410
    assert retry_response.status_code == 410
    assert Deck.objects.filter(owner=owner, client_creation_id=creation_key).count() == 0
    creation = DeckCreation.objects.get(owner=owner, client_creation_id=creation_key)
    assert creation.deck_id is None


def test_deck_create_rejects_malformed_idempotency_key() -> None:
    username = "deck-invalid-idempotency-user"
    password = "password"
    _create_user(username, password)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
        HTTP_IDEMPOTENCY_KEY="not-a-uuid",
    )

    assert response.status_code == 400
    assert Deck.objects.count() == 0


def test_deck_create_preserves_submitted_board_entry_order() -> None:
    username = "deck-create-entry-order-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Create Order Hero", hero=True)
    alpha_card = _create_card(name="Create Order Alpha", hero=False, type_labels=["Mana"])
    beta_card = _create_card(name="Create Order Beta", hero=False, type_labels=["Mana"])
    gamma_card = _create_card(name="Create Order Gamma", hero=False, type_labels=["Mana"])
    filler_cards = _build_mainboard_cards(total_unique=12)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Create Entry Order Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": gamma_card.id, "quantity": 4},
                {"card_id": alpha_card.id, "quantity": 4},
                {"card_id": beta_card.id, "quantity": 4},
                *_valid_entries(filler_cards),
            ],
            "sideboards": [
                {
                    "name": "Flex",
                    "entries": [
                        {"card_id": beta_card.id, "quantity": 2},
                        {"card_id": alpha_card.id, "quantity": 1},
                    ],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    payload = response.json()
    assert [entry["card"]["id"] for entry in payload["mainboard"]["entries"][:3]] == [
        gamma_card.id,
        alpha_card.id,
        beta_card.id,
    ]
    assert [entry["card"]["id"] for entry in payload["sideboards"][0]["entries"]] == [
        beta_card.id,
        alpha_card.id,
    ]


def test_patch_preserves_sideboards_when_omitted() -> None:
    username = "deck-patch-preserve-sideboards-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Patch Preserve Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Patch Preserve Sideboard Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/my/decks",
        data={
            "name": "Patch Preserve Deck",
            "description": "Before update",
            "visibility": "public",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
            "sideboards": [
                {
                    "name": "Flex",
                    "entries": [{"card_id": sideboard_card.id, "quantity": 3}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"name": "Patch Preserve Deck Updated"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["name"] == "Patch Preserve Deck Updated"
    assert payload["description"] == "Before update"
    assert payload["sideboards"] == [
        {
            "id": payload["sideboards"][0]["id"],
            "name": "Flex",
            "total_cards": 3,
            "unique_cards": 1,
            "entries": [
                {
                    "quantity": 3,
                    "card": payload["sideboards"][0]["entries"][0]["card"],
                }
            ],
        }
    ]


def test_patch_clears_sideboards_when_explicitly_empty() -> None:
    username = "deck-patch-clear-sideboards-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Patch Clear Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Patch Clear Sideboard Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/my/decks",
        data={
            "name": "Patch Clear Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
            "sideboards": [
                {
                    "name": "Flex",
                    "entries": [{"card_id": sideboard_card.id, "quantity": 2}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"sideboards": []},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["sideboards"] == []
    assert payload["totals"]["overall_total_cards"] == payload["totals"]["mainboard_total_cards"] == 60


def test_deck_patch_persists_reordered_board_entries() -> None:
    username = "deck-patch-entry-order-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Patch Order Hero", hero=True)
    alpha_card = _create_card(name="Patch Order Alpha", hero=False, type_labels=["Mana"])
    beta_card = _create_card(name="Patch Order Beta", hero=False, type_labels=["Mana"])
    gamma_card = _create_card(name="Patch Order Gamma", hero=False, type_labels=["Mana"])
    filler_cards = _build_mainboard_cards(total_unique=12)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/my/decks",
        data={
            "name": "Patch Entry Order Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": alpha_card.id, "quantity": 4},
                {"card_id": beta_card.id, "quantity": 4},
                {"card_id": gamma_card.id, "quantity": 4},
                *_valid_entries(filler_cards),
            ],
            "sideboards": [
                {
                    "name": "Flex",
                    "entries": [
                        {"card_id": alpha_card.id, "quantity": 1},
                        {"card_id": beta_card.id, "quantity": 2},
                    ],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/my/decks/{deck_id}",
        data={
            "entries": [
                {"card_id": gamma_card.id, "quantity": 4},
                {"card_id": alpha_card.id, "quantity": 4},
                {"card_id": beta_card.id, "quantity": 4},
                *_valid_entries(filler_cards),
            ],
            "sideboards": [
                {
                    "name": "Flex",
                    "entries": [
                        {"card_id": beta_card.id, "quantity": 2},
                        {"card_id": alpha_card.id, "quantity": 1},
                    ],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    detail_response = client.get(f"/my/decks/{deck_id}")

    assert patch_response.status_code == 200
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert [entry["card"]["id"] for entry in payload["mainboard"]["entries"][:3]] == [
        gamma_card.id,
        alpha_card.id,
        beta_card.id,
    ]
    assert [entry["card"]["id"] for entry in payload["sideboards"][0]["entries"]] == [
        beta_card.id,
        alpha_card.id,
    ]


def test_patch_preserves_mainboard_when_entries_omitted() -> None:
    username = "deck-patch-preserve-entries-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Patch Preserve Entries Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    create_response = client.post(
        "/my/decks",
        data={
            "name": "Patch Preserve Entries Deck",
            "description": None,
            "visibility": "public",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert create_response.status_code == 201
    deck_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/my/decks/{deck_id}",
        data={"description": "Entries unchanged"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["description"] == "Entries unchanged"
    assert payload["mainboard"]["total_cards"] == 60
    assert len(payload["mainboard"]["entries"]) == 15


def test_sideboard_name_is_required() -> None:
    username = "deck-sideboard-name-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard Name Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Nameless Sideboard Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Invalid Sideboard Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
            "sideboards": [
                {
                    "name": "",
                    "entries": [{"card_id": sideboard_card.id, "quantity": 2}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400


def test_sideboards_reject_hero_cards() -> None:
    username = "deck-sideboard-hero-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard Hero Reject", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Invalid Hero Sideboard Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
            "sideboards": [
                {
                    "name": "Heroes?",
                    "entries": [{"card_id": hero.id, "quantity": 2}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Hero cards cannot appear in sideboards."


def test_sideboards_reject_quantities_above_100() -> None:
    username = "deck-sideboard-quantity-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard Quantity Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Large Sideboard Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Too Large Sideboard Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
            "sideboards": [
                {
                    "name": "Overflow",
                    "entries": [{"card_id": sideboard_card.id, "quantity": 101}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400


def test_deck_create_warns_for_multiple_legendary_mainboard_copies() -> None:
    username = "deck-legendary-mainboard-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Legendary Limit Hero", hero=True)
    legendary_card = _create_card(name="Legendary Mainboard Card", hero=False, type_labels=["Legendary"])
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Too Many Legendary Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": legendary_card.id, "quantity": 2},
                *_valid_entries(mainboard_cards),
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"]["is_valid"] is True
    assert payload["status"]["issues"] == []
    assert payload["status"]["warnings"] == ["Legendary cards are limited to 1 copy per deck."]


def test_deck_update_uses_legendary_scope_for_warnings() -> None:
    username = "deck-legendary-sideboard-user"
    password = "password"
    owner = _create_user(username, password)
    hero = _create_card(
        name="Legendary Sideboard Hero",
        hero=True,
        deck_building_config={
            "overrides": {
                "legendary_copy_limit": {
                    "scope": "whole_deck",
                }
            }
        },
    )
    legendary_card = _create_card(name="Legendary Sideboard Card", hero=False, type_labels=["Legendary"])
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Legendary Sideboard Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/my/decks/{deck.id}",
        data={
            "name": "Legendary Sideboard Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": legendary_card.id, "quantity": 1},
                *_valid_entries(mainboard_cards),
            ],
            "sideboards": [
                {
                    "name": "Legends",
                    "entries": [{"card_id": legendary_card.id, "quantity": 1}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert response.json()["status"]["warnings"] == ["Legendary cards are limited to 1 copy per deck."]


def test_deck_create_allows_one_legendary_copy_and_large_non_legendary_sideboard() -> None:
    username = "deck-legendary-valid-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Valid Legendary Hero", hero=True)
    legendary_card = _create_card(name="Valid Legendary Card", hero=False, type_labels=["Legendary"])
    sideboard_card = _create_card(name="Valid Large Sideboard Card", hero=False)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Valid Legendary Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": legendary_card.id, "quantity": 1},
                *_valid_entries(mainboard_cards),
            ],
            "sideboards": [
                {
                    "name": "Overflow",
                    "entries": [{"card_id": sideboard_card.id, "quantity": 100}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201


def test_deck_create_rejects_non_legendary_mainboard_copies_above_four() -> None:
    username = "deck-mainboard-limit-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Mainboard Limit Hero", hero=True)
    limited_card = _create_card(name="Mainboard Limited Card", hero=False)
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Too Many Copies Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": limited_card.id, "quantity": 5},
                *_valid_entries(mainboard_cards),
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Each mainboard card quantity must be between 1 and 4."


def test_hero_override_allows_six_mainboard_copies() -> None:
    username = "deck-mainboard-override-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(
        name="Mainboard Override Hero",
        hero=True,
        deck_building_config={
            "overrides": {
                "mainboard_copy_limit": {
                    "max": 6,
                }
            }
        },
    )
    limited_card = _create_card(name="Mainboard Six Copy Card", hero=False)
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Six Copies Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": limited_card.id, "quantity": 6},
                *_valid_entries(mainboard_cards),
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["deck_building_rules"]["mainboard_copy_limit"]["max"] == 6


def test_card_self_override_allows_only_that_card_above_default_copy_limit() -> None:
    username = "deck-self-copy-limit-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Self Copy Limit Hero", hero=True)
    self_limited_card = _create_card(
        name="Self Six Copy Card",
        hero=False,
        deck_building_config={
            "overrides": {
                "mainboard_copy_limit": {
                    "applies_to": "self",
                    "max": 6,
                }
            }
        },
    )
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Self Six Copies Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": self_limited_card.id, "quantity": 6},
                *_valid_entries(mainboard_cards),
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["deck_building_rules"]["mainboard_copy_limit"]["max"] == 4


def test_card_self_override_does_not_raise_other_cards_copy_limit() -> None:
    username = "deck-self-copy-limit-other-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Self Copy Limit Other Hero", hero=True)
    self_limited_card = _create_card(
        name="Self Limit Source Card",
        hero=False,
        deck_building_config={
            "overrides": {
                "mainboard_copy_limit": {
                    "applies_to": "self",
                    "max": 6,
                }
            }
        },
    )
    other_limited_card = _create_card(name="Default Limited Other Card", hero=False)
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Self Limit Does Not Leak Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": self_limited_card.id, "quantity": 1},
                {"card_id": other_limited_card.id, "quantity": 5},
                *_valid_entries(mainboard_cards),
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Each mainboard card quantity must be between 1 and 4."


def test_card_self_legendary_limit_applies_only_to_that_legendary_card() -> None:
    username = "deck-self-legendary-limit-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Self Legendary Hero", hero=True)
    self_limited_legendary = _create_card(
        name="Self Limited Legendary",
        hero=False,
        type_labels=["Legendary"],
        deck_building_config={
            "overrides": {
                "legendary_copy_limit": {
                    "applies_to": "self",
                    "severity": "hard",
                    "blocks_action": True,
                    "max": 1,
                }
            }
        },
    )
    other_legendary = _create_card(name="Other Soft Legendary", hero=False, type_labels=["Legendary"])
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Self Legendary Does Not Leak Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": self_limited_legendary.id, "quantity": 1},
                {"card_id": other_legendary.id, "quantity": 2},
                *_valid_entries(mainboard_cards),
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["status"]["warnings"] == ["Legendary cards are limited to 1 copy per deck."]

    blocked_response = client.post(
        "/my/decks",
        data={
            "name": "Self Legendary Blocks Owner",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": self_limited_legendary.id, "quantity": 2},
                *_valid_entries(mainboard_cards),
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert blocked_response.status_code == 400
    assert blocked_response.json()["detail"] == "Legendary cards are limited to 1 copy per deck."


def test_card_deck_building_overrides_resolve_independent_of_entry_order() -> None:
    first_card = _create_card(
        name="Ordered Override First",
        hero=False,
        deck_building_config={
            "overrides": {
                "mainboard_copy_limit": {
                    "max": 1,
                }
            }
        },
    )
    second_card = _create_card(
        name="Ordered Override Second",
        hero=False,
        deck_building_config={
            "overrides": {
                "mainboard_copy_limit": {
                    "max": 6,
                }
            }
        },
    )
    evaluator = DeckConstraintEvaluator()
    entries = [
        DeckConstraintEntry(card=first_card, quantity=1, board="mainboard"),
        DeckConstraintEntry(card=second_card, quantity=1, board="mainboard"),
    ]

    forward_rules = evaluator.resolve_rules(hero_card=None, entries=entries).to_json()
    reverse_rules = evaluator.resolve_rules(hero_card=None, entries=list(reversed(entries))).to_json()

    assert forward_rules == reverse_rules


def test_whole_deck_mainboard_copy_scope_counts_sideboard_copies() -> None:
    username = "deck-whole-copy-scope-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(
        name="Whole Copy Scope Hero",
        hero=True,
        deck_building_config={
            "overrides": {
                "mainboard_copy_limit": {
                    "scope": "whole_deck",
                    "max": 4,
                }
            }
        },
    )
    limited_card = _create_card(name="Whole Copy Limited Card", hero=False)
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Whole Copy Scope Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": [
                {"card_id": limited_card.id, "quantity": 4},
                *_valid_entries(mainboard_cards),
            ],
            "sideboards": [
                {
                    "name": "Copies",
                    "entries": [{"card_id": limited_card.id, "quantity": 1}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Each mainboard card quantity must be between 1 and 4."


def test_whole_deck_mainboard_card_count_scope_counts_sideboard_cards() -> None:
    username = "deck-whole-count-scope-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(
        name="Whole Count Scope Hero",
        hero=True,
        deck_building_config={
            "overrides": {
                "mainboard_card_count": {
                    "scope": "whole_deck",
                    "max": 100,
                }
            }
        },
    )
    mainboard_cards = _build_mainboard_cards(total_unique=20)
    sideboard_card = _create_card(name="Whole Count Sideboard Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Whole Count Scope Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
            "sideboards": [
                {
                    "name": "Overflow",
                    "entries": [{"card_id": sideboard_card.id, "quantity": 30}],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Deck cannot contain more than 100 mainboard cards."


def test_sideboards_reject_duplicate_cards_within_same_sideboard() -> None:
    username = "deck-sideboard-duplicate-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard Duplicate Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Duplicate Sideboard Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Duplicate Sideboard Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": hero.id,
            "entries": _valid_entries(mainboard_cards),
            "sideboards": [
                {
                    "name": "Dupes",
                    "entries": [
                        {"card_id": sideboard_card.id, "quantity": 2},
                        {"card_id": sideboard_card.id, "quantity": 3},
                    ],
                }
            ],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Each card can only appear once within a sideboard."


def test_non_owner_cannot_update_or_delete_deck() -> None:
    owner = _create_user("deck-owner-locked", "password")
    other_user = _create_user("deck-other-locked", "password")
    hero = _create_card(name="Locked Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Locked Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, other_user.username, "password")

    get_response = client.get(f"/my/decks/{deck.id}")
    patch_response = client.patch(
        f"/my/decks/{deck.id}",
        data={
            "name": "Nope",
            "description": None,
            "visibility": "public",
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

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


def test_staff_can_edit_another_users_deck_but_not_delete_it() -> None:
    owner = _create_user("deck-staff-tag-owner", "password")
    staff = _create_user("deck-staff-tag-manager", "password", is_staff=True)
    hero = _create_card(name="Staff Tag Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    role = DeckTag.objects.create(kind="role", key="staff-control", label="Staff Control")
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Staff Managed Tags",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
        suggested_type_labels=["Pending Staff Type"],
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, staff.username, "password")

    detail_response = client.get(f"/my/decks/{deck.id}")
    update_response = client.patch(
        f"/my/decks/{deck.id}",
        data={
            "name": "Staff Renamed Deck",
            "description": "Updated by staff",
            "visibility": "public",
            "hero_card_id": hero.id,
            "entries": [{"card_id": card.id, "quantity": 4} for card in mainboard_cards],
            "sideboards": [],
            "tag_ids": [role.id],
            "suggested_type_labels": [],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    delete_response = client.delete(
        f"/my/decks/{deck.id}",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["pending_tag_suggestions"][0]["label"] == "Pending Staff Type"
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Staff Renamed Deck"
    assert update_response.json()["description"] == "Updated by staff"
    assert update_response.json()["visibility"] == "public"
    assert update_response.json()["tags"] == [
        {"id": role.id, "key": role.key, "label": role.label, "kind": role.kind}
    ]
    assert update_response.json()["pending_tag_suggestions"] == []
    assert delete_response.status_code == 404
    deck.refresh_from_db()
    assert deck.name == "Staff Renamed Deck"
    assert deck.description == "Updated by staff"
    assert deck.visibility == "public"
    assert deck.tag_assignments.get().tag_id == role.id


def test_unauthenticated_users_are_blocked_from_my_decks() -> None:
    client = Client(HTTP_HOST="localhost")

    response = client.get("/my/decks")

    assert response.status_code in {401, 403}


def test_deck_create_rejects_non_hero_card_as_hero() -> None:
    username = "deck-invalid-hero-user"
    password = "password"
    _create_user(username, password)
    non_hero = _create_card(name="Not Hero", hero=False)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Invalid Hero Deck",
            "description": None,
            "visibility": "private",
            "hero_card_id": non_hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Hero card must be marked as a hero."


def test_deck_create_allows_invalid_in_progress_drafts_below_minimum_card_count() -> None:
    username = "deck-invalid-count-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Count Hero", hero=True)
    mainboard_cards = _build_mainboard_cards()
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Draft Deck",
            "description": None,
            "visibility": "public",
            "hero_card_id": hero.id,
            "entries": [{"card_id": card.id, "quantity": 1} for card in mainboard_cards[:10]],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["status"]["is_valid"] is False
    assert response.json()["status"]["label"] == "In Progress"
    assert response.json()["status"]["issues"] == ["Deck must contain at least 20 mainboard cards."]


def test_deck_create_marks_deck_invalid_without_enough_mana_type_cards() -> None:
    username = "deck-invalid-mana-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Mana Count Hero", hero=True)
    non_mana_cards = [_create_card(name=f"Non Mana Card {index}", hero=False) for index in range(20)]
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "No Mana Deck",
            "description": None,
            "visibility": "public",
            "hero_card_id": hero.id,
            "entries": [{"card_id": card.id, "quantity": 1} for card in non_mana_cards],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["status"]["is_valid"] is False
    assert response.json()["status"]["issues"] == ["Deck must contain at least 3 mainboard cards with type 'Mana'."]


def test_hero_override_allows_deck_without_mana_type_cards() -> None:
    username = "deck-mana-override-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(
        name="Mana Override Hero",
        hero=True,
        deck_building_config={
            "overrides": {
                "mana_type_count": {
                    "min": 0,
                }
            }
        },
    )
    non_mana_cards = [_create_card(name=f"Override Non Mana Card {index}", hero=False) for index in range(20)]
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "No Mana Override Deck",
            "description": None,
            "visibility": "public",
            "hero_card_id": hero.id,
            "entries": [{"card_id": card.id, "quantity": 1} for card in non_mana_cards],
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["status"]["is_valid"] is True
    assert response.json()["status"]["issues"] == []


def test_deck_create_rejects_hero_in_mainboard() -> None:
    username = "deck-invalid-duplicate-hero-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Duplicate Hero", hero=True)
    mainboard_cards = _build_mainboard_cards(total_unique=14)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.post(
        "/my/decks",
        data={
            "name": "Invalid Duplicate Hero Deck",
            "description": None,
            "visibility": "private",
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


def test_cards_list_can_filter_by_card_role() -> None:
    hero_card = _create_card(name="Filter Hero", hero=True)
    non_hero_card = _create_card(name="Filter Non Hero", hero=False)
    client = Client(HTTP_HOST="localhost")

    hero_response = client.get("/cards", {"card_roles": "hero"})
    non_hero_response = client.get("/cards", {"card_roles": "standard"})

    assert hero_response.status_code == 200
    assert non_hero_response.status_code == 200
    assert hero_card.id in {row["id"] for row in hero_response.json()["results"]}
    assert non_hero_card.id not in {row["id"] for row in hero_response.json()["results"]}
    assert non_hero_card.id in {row["id"] for row in non_hero_response.json()["results"]}


def test_card_role_filters_support_any_all_and_exclusions() -> None:
    hero_card = _create_card(name="Role Matching Hero", hero=True)
    boon_event_card = _create_card(name="Role Matching Boon Event", hero=False)
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card=boon_event_card, role="boon"),
            CardRoleAssignment(card=boon_event_card, role="event"),
        ]
    )
    standard_card = _create_card(name="Role Matching Standard", hero=False)
    client = Client(HTTP_HOST="localhost")

    any_ids = {
        row["id"]
        for row in client.get(
            "/cards",
            {"card_roles": ["hero", "boon"], "card_role_match": "any"},
        ).json()["results"]
    }
    all_ids = {
        row["id"]
        for row in client.get(
            "/cards",
            {"card_roles": ["boon", "event"], "card_role_match": "all"},
        ).json()["results"]
    }
    excluded_ids = {
        row["id"]
        for row in client.get(
            "/cards",
            {"card_role_exclude": ["hero", "event"]},
        ).json()["results"]
    }

    assert {hero_card.id, boon_event_card.id} <= any_ids
    assert boon_event_card.id in all_ids
    assert hero_card.id not in all_ids
    assert standard_card.id in excluded_ids
    assert hero_card.id not in excluded_ids
    assert boon_event_card.id not in excluded_ids


def test_game_master_cards_are_staff_scoped_for_lists_and_details() -> None:
    gm_card = _create_card(name="Restricted Game Master Event", hero=False)
    gm_card.card_pool = "game_master"
    gm_card.save(update_fields=["card_pool"])
    CardRoleAssignment.objects.create(card=gm_card, role="event")
    anonymous = Client(HTTP_HOST="localhost")

    assert anonymous.get("/cards", {"card_pool": "game_master"}).status_code == 403
    assert anonymous.get(f"/cards/{gm_card.id}").status_code == 404
    assert gm_card.id not in {row["id"] for row in anonymous.get("/cards").json()["results"]}

    username = "gm-card-list-staff"
    password = "password"
    _create_user(username, password, is_staff=True)
    staff = Client(HTTP_HOST="localhost")
    assert staff.login(username=username, password=password)
    response = staff.get("/cards", {"card_pool": "game_master", "card_roles": "event"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [gm_card.id]


def test_deck_writes_treat_game_master_card_ids_as_missing_player_cards() -> None:
    username = "gm-deck-write-scope-user"
    password = "password"
    _create_user(username, password)
    player_hero = _create_card(name="GM Write Player Hero", hero=True)
    game_master_hero = _create_card(name="GM Write Secret Hero", hero=True)
    game_master_card = _create_card(name="GM Write Secret Card", hero=False)
    Card.objects.filter(id__in=[game_master_hero.id, game_master_card.id]).update(
        card_pool="game_master"
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    def create_response(
        *,
        hero_card_id: str,
        entries: list[dict[str, object]],
        sideboards: list[dict[str, object]] | None = None,
    ) -> HttpResponse:
        return client.post(
            "/my/decks",
            data={
                "name": "GM Write Scope Deck",
                "visibility": "private",
                "hero_card_id": hero_card_id,
                "entries": entries,
                "sideboards": sideboards or [],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

    restricted_hero_response = create_response(hero_card_id=game_master_hero.id, entries=[])
    missing_hero_response = create_response(hero_card_id="missing-hero", entries=[])
    restricted_entry_response = create_response(
        hero_card_id=player_hero.id,
        entries=[{"card_id": game_master_card.id, "quantity": 1}],
    )
    missing_entry_response = create_response(
        hero_card_id=player_hero.id,
        entries=[{"card_id": "missing-card", "quantity": 1}],
    )
    restricted_sideboard_response = create_response(
        hero_card_id=player_hero.id,
        entries=[],
        sideboards=[
            {
                "name": "Restricted",
                "entries": [{"card_id": game_master_card.id, "quantity": 1}],
            }
        ],
    )
    missing_sideboard_response = create_response(
        hero_card_id=player_hero.id,
        entries=[],
        sideboards=[
            {
                "name": "Missing",
                "entries": [{"card_id": "missing-card", "quantity": 1}],
            }
        ],
    )

    assert restricted_hero_response.status_code == 400
    assert restricted_hero_response.json() == missing_hero_response.json() == {
        "detail": "Hero card not found."
    }
    assert restricted_entry_response.status_code == 400
    assert restricted_entry_response.json() == missing_entry_response.json() == {
        "detail": "One or more selected mainboard cards do not exist."
    }
    assert restricted_sideboard_response.status_code == 400
    assert restricted_sideboard_response.json() == missing_sideboard_response.json() == {
        "detail": "One or more selected sideboard cards do not exist."
    }


def test_reclassified_game_master_card_is_redacted_in_owner_deck_but_visible_to_staff() -> None:
    owner = _create_user("gm-deck-owner", "password")
    staff = _create_user("gm-deck-staff", "password", is_staff=True)
    hero = _create_card(name="GM Deck Player Hero", hero=True)
    reclassified = _create_card(name="Secret Reclassified Event", hero=False)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="Reclassified Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=reclassified.id, quantity=1)],
        sideboards=[],
    )
    reclassified.card_pool = "game_master"
    reclassified.lifecycle_status = "deprecated"
    reclassified.deck_building_config_json = {
        "overrides": {"mainboard_copy_limit": {"max": 73}},
    }
    reclassified.save(update_fields=["card_pool", "lifecycle_status", "deck_building_config_json"])
    CardRoleAssignment.objects.create(card=reclassified, role="event")

    owner_client = Client(HTTP_HOST="localhost")
    owner_client.force_login(owner)
    owner_response = owner_client.get(f"/my/decks/{deck.id}")

    assert owner_response.status_code == 200
    owner_payload = owner_response.json()
    assert owner_payload["status"]["is_valid"] is False
    assert owner_payload["status"]["issues"] == [
        "Deck contains cards that are unavailable in the Player workspace."
    ]
    assert owner_payload["deck_building_rules"]["mainboard_copy_limit"]["max"] == 4
    restricted_card = owner_payload["mainboard"]["entries"][0]["card"]
    assert restricted_card["restricted"] is True
    assert restricted_card["name"] == "Restricted Game Master card"
    assert restricted_card["lifecycle_status"] == "active"
    assert "Secret Reclassified Event" not in owner_response.content.decode()
    assert '"max": 73' not in owner_response.content.decode()
    owner_search_response = owner_client.get(
        "/my/decks",
        {"view": "summary", "q": "Secret Reclassified Event"},
    )
    assert owner_search_response.status_code == 200
    assert owner_search_response.json() == []
    owner_summary_response = owner_client.get("/my/decks", {"view": "summary"})
    assert owner_summary_response.status_code == 200
    owner_summary = next(row for row in owner_summary_response.json() if row["id"] == deck.id)
    assert owner_summary["status"] == {
        "is_valid": False,
        "label": "In Progress",
        "deprecated_card_count": 0,
    }

    staff_client = Client(HTTP_HOST="localhost")
    staff_client.force_login(staff)
    staff_response = staff_client.get(f"/my/decks/{deck.id}")

    assert staff_response.status_code == 200
    assert staff_response.json()["mainboard"]["entries"][0]["card"]["name"].startswith(
        "Secret Reclassified Event"
    )
    assert staff_response.json()["deck_building_rules"]["mainboard_copy_limit"]["max"] == 73
    owner.is_staff = True
    owner.save(update_fields=["is_staff"])
    staff_owner_client = Client(HTTP_HOST="localhost")
    staff_owner_client.force_login(owner)
    staff_search_response = staff_owner_client.get(
        "/my/decks",
        {"view": "summary", "q": "Secret Reclassified Event"},
    )
    assert [row["id"] for row in staff_search_response.json()] == [deck.id]


def test_standard_cannot_match_all_with_persisted_roles() -> None:
    response = Client(HTTP_HOST="localhost").get(
        "/cards",
        {"card_roles": ["standard", "hero"], "card_role_match": "all"},
    )
    repository_result = list_cards(
        query=None,
        max_confidence=None,
        card_roles=["standard", "hero"],
        card_role_match="all",
    )

    assert response.status_code == 400
    assert repository_result.count == 0
    assert repository_result.results == []


def test_cards_list_hides_deprecated_cards_by_default_but_can_include_them() -> None:
    active_card = _create_card(name="Active Lifecycle Card", hero=False)
    deprecated_card = _create_card(
        name="Deprecated Lifecycle Card",
        hero=False,
        lifecycle_status="deprecated",
    )
    client = Client(HTTP_HOST="localhost")

    default_response = client.get("/cards")
    deprecated_response = client.get(
        "/cards",
        {"q": "Deprecated Lifecycle Card", "lifecycle_status": "deprecated"},
    )
    all_response = client.get("/cards", {"q": "Deprecated Lifecycle Card", "lifecycle_status": "all"})
    detail_response = client.get(f"/cards/{deprecated_card.id}")

    assert default_response.status_code == 200
    assert deprecated_response.status_code == 200
    assert all_response.status_code == 200
    assert detail_response.status_code == 200
    assert active_card.id in {row["id"] for row in default_response.json()["results"]}
    assert deprecated_card.id not in {row["id"] for row in default_response.json()["results"]}
    assert {row["id"] for row in deprecated_response.json()["results"]} == {deprecated_card.id}
    assert deprecated_card.id in {row["id"] for row in all_response.json()["results"]}
    assert detail_response.json()["lifecycle_status"] == "deprecated"


def test_latest_version_patch_can_update_card_roles() -> None:
    username = "deck-card-hero-toggle-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Toggle Hero Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"card_pool": "game_master", "card_roles": ["hero", "boon"]},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert set(card.role_assignments.values_list("role", flat=True)) == {"hero", "boon"}
    card.refresh_from_db()
    assert card.card_pool == "game_master"
    assert response.json()["card_pool"] == "game_master"
    assert set(response.json()["card_roles"]) == {"hero", "boon"}

    replacement_response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"card_pool": "player", "card_roles": ["event"]},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert replacement_response.status_code == 200
    card.refresh_from_db()
    assert card.card_pool == "player"
    assert list(card.role_assignments.values_list("role", flat=True)) == ["event"]


def test_latest_version_patch_can_deprecate_card() -> None:
    username = "deck-card-lifecycle-toggle-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Toggle Lifecycle Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"lifecycle_status": "deprecated"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    card.refresh_from_db()
    assert card.lifecycle_status == "deprecated"
    assert response.json()["lifecycle_status"] == "deprecated"


def test_latest_version_patch_rejects_non_object_deck_building_overrides() -> None:
    username = "deck-card-invalid-overrides-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Invalid Overrides Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"deck_building_config": {"overrides": []}},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Deck-building config overrides must be a JSON object."


def test_latest_version_patch_rejects_boolean_deck_building_numeric_values() -> None:
    username = "deck-card-boolean-rule-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Boolean Rule Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"deck_building_config": {"overrides": {"mainboard_copy_limit": {"max": True}}}},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Deck-building numeric rule values must be non-negative integers."


def test_latest_version_patch_rejects_duplicate_deck_building_numeric_aliases() -> None:
    username = "deck-card-duplicate-rule-alias-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Duplicate Rule Alias Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"deck_building_config": {"overrides": {"mana_type_count": {"min": 10, "count": 0}}}},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Deck-building numeric aliases cannot be combined for the same rule."


def test_latest_version_patch_rejects_invalid_deck_building_applies_to() -> None:
    username = "deck-card-invalid-applies-to-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Invalid Applies To Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"deck_building_config": {"overrides": {"mainboard_copy_limit": {"applies_to": "card"}}}},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Deck-building applies_to must be 'deck' or 'self'."


def test_latest_version_patch_rejects_self_applies_to_for_deck_aggregate_rules() -> None:
    username = "deck-card-self-applies-to-aggregate-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Invalid Self Aggregate Rule Card", hero=False)
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, username, password)

    response = client.patch(
        f"/cards/{card.id}/latest-version",
        data={"deck_building_config": {"overrides": {"mainboard_card_count": {"applies_to": "self"}}}},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Deck-building applies_to 'self' is only supported for card-specific rules."


def test_deck_tag_catalog_defaults_and_admin_permissions() -> None:
    public_response = Client(HTTP_HOST="localhost").get("/deck-tags")

    assert public_response.status_code == 200
    assert {row["label"] for row in public_response.json()["roles"]} >= {
        "Damage",
        "Healing",
        "Control",
        "Tank",
        "Support",
    }
    assert {row["label"] for row in public_response.json()["types"]} >= {
        "Countermagic",
        "Armor",
        "Team Card Draw",
        "New Player",
    }

    non_staff = _create_user("deck-tag-catalog-user", "password")
    staff = _create_user("deck-tag-catalog-staff", "password", is_staff=True)
    non_staff_client = Client(HTTP_HOST="localhost")
    staff_client = Client(HTTP_HOST="localhost")
    non_staff_client.force_login(non_staff)
    staff_client.force_login(staff)

    assert Client(HTTP_HOST="localhost").get("/admin/deck-tags").status_code == 403
    assert non_staff_client.get("/admin/deck-tags").status_code == 403
    assert staff_client.get("/admin/deck-tags").status_code == 200


def test_deck_tag_suggestions_are_owner_only_normalized_and_resolved_across_decks() -> None:
    owner = _create_user("deck-tag-owner", "password")
    hero = _create_card(name="Deck Tag Hero", hero=True)
    cards = _build_mainboard_cards()
    role = DeckTag.objects.get(kind="role", key="damage")
    service = DeckService()

    first_deck = service.create_owner_deck(
        owner_id=str(owner.pk),
        name="First Tagged Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in cards],
        sideboards=[],
        tag_ids=[role.id],
        suggested_type_labels=["Tempo Burst"],
    )
    second_deck = service.create_owner_deck(
        owner_id=str(owner.pk),
        name="Second Tagged Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in cards],
        sideboards=[],
        suggested_type_labels=["  tempo   burst  "],
    )

    suggestions = DeckTagSuggestion.objects.filter(normalized_value="tempo burst")
    assert suggestions.count() == 1
    suggestion = suggestions.get()
    assert suggestion.deck_occurrences.count() == 2

    owner_client = Client(HTTP_HOST="localhost")
    owner_client.force_login(owner)
    owner_payload = owner_client.get(f"/my/decks/{first_deck.id}").json()
    public_payload = Client(HTTP_HOST="localhost").get(f"/decks/{first_deck.id}").json()
    assert owner_payload["pending_tag_suggestions"][0]["normalized_value"] == "tempo burst"
    assert public_payload["pending_tag_suggestions"] == []

    service.update_owner_deck(
        deck_id=first_deck.id,
        owner_id=str(owner.pk),
        updates=DeckUpdateInput(update_tags=True, tag_ids=[role.id]),
    )
    assert suggestion.deck_occurrences.filter(deck=first_deck).exists()

    accepted = DeckTagService().accept_suggestion_as_new(suggestion_id=suggestion.id)
    assert accepted is not None
    assert accepted.accepted_tag is not None
    assert DeckTagAssignment.objects.filter(deck=first_deck, tag=accepted.accepted_tag).exists()
    assert DeckTagAssignment.objects.filter(deck=second_deck, tag=accepted.accepted_tag).exists()
    assert suggestion.deck_occurrences.filter(is_active=True).count() == 0
    assert owner_client.get(f"/my/decks/{first_deck.id}").json()["pending_tag_suggestions"] == []

    service.update_owner_deck(
        deck_id=first_deck.id,
        owner_id=str(owner.pk),
        updates=DeckUpdateInput(
            update_tags=True,
            tag_ids=[role.id],
            suggested_type_labels=["Rejected Deck Type"],
        ),
    )
    service.update_owner_deck(
        deck_id=second_deck.id,
        owner_id=str(owner.pk),
        updates=DeckUpdateInput(
            update_tags=True,
            suggested_type_labels=["Rejected Deck Type"],
        ),
    )
    rejected = DeckTagSuggestion.objects.get(normalized_value="rejected deck type")
    DeckTagService().reject_suggestion(suggestion_id=rejected.id)
    assert rejected.deck_occurrences.filter(is_active=True).count() == 0
    assert owner_client.get(f"/my/decks/{first_deck.id}").json()["pending_tag_suggestions"] == []

    resubmit_response = owner_client.patch(
        f"/my/decks/{first_deck.id}",
        data={
            "tag_ids": [role.id],
            "suggested_type_labels": ["REJECTED DECK TYPE"],
        },
        content_type="application/json",
    )

    assert resubmit_response.status_code == 200
    assert resubmit_response.json()["tag_suggestion_results"] == [
        {
            "label": "REJECTED DECK TYPE",
            "normalized_value": "rejected deck type",
            "status": "rejected",
            "message": "This tag was previously declined. Try a more specific suggestion.",
            "suggestion_id": rejected.id,
            "tag": None,
        }
    ]
    rejected.refresh_from_db()
    assert rejected.rejected_resubmission_count == 1
    assert rejected.deck_occurrences.get(deck=first_deck).is_active is True
    assert rejected.deck_occurrences.get(deck=second_deck).is_active is False
    assert owner_client.get(f"/my/decks/{first_deck.id}").json()["pending_tag_suggestions"] == []

    staff = _create_user("deck-tag-reopen-staff", "password", is_staff=True)
    staff_client = Client(HTTP_HOST="localhost")
    staff_client.force_login(staff)
    catalog_response = staff_client.get("/admin/deck-tags")
    suggestion_row = next(
        row for row in catalog_response.json()["suggested_types"] if row["id"] == rejected.id
    )
    assert suggestion_row["active_occurrence_count"] == 1
    assert "linked_decks" not in suggestion_row

    detail_response = staff_client.get(f"/admin/deck-tag-suggestions/{rejected.id}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["linked_decks"]) == 2

    duplicate_reject_response = staff_client.post(f"/admin/deck-tag-suggestions/{rejected.id}/reject")
    assert duplicate_reject_response.status_code == 400
    assert duplicate_reject_response.json()["detail"] == "Only pending deck tag suggestions can be rejected."

    reopen_response = staff_client.post(f"/admin/deck-tag-suggestions/{rejected.id}/reopen")

    assert reopen_response.status_code == 200
    assert reopen_response.json()["status"] == "pending"
    assert reopen_response.json()["active_occurrence_count"] == 1
    assert reopen_response.json()["rejected_resubmission_count"] == 1
    assert owner_client.get(f"/my/decks/{first_deck.id}").json()["pending_tag_suggestions"][0]["id"] == rejected.id
    assert owner_client.get(f"/my/decks/{second_deck.id}").json()["pending_tag_suggestions"] == []

    remove_response = owner_client.patch(
        f"/my/decks/{first_deck.id}",
        data={"tag_ids": [role.id], "suggested_type_labels": []},
        content_type="application/json",
    )
    assert remove_response.status_code == 200
    rejected_occurrence = rejected.deck_occurrences.get(deck=first_deck)
    rejected_occurrence.refresh_from_db()
    assert rejected_occurrence.is_active is False
    assert owner_client.get(f"/my/decks/{first_deck.id}").json()["pending_tag_suggestions"] == []


def test_deck_tag_suggestion_resolution_is_terminal_and_target_changes_reject_it() -> None:
    owner = _create_user("deck-tag-transition-owner", "password")
    hero = _create_card(name="Deck Tag Transition Hero", hero=True)
    cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Deck Tag Transition Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in cards],
        sideboards=[],
        suggested_type_labels=["Transition Type"],
    )
    service = DeckTagService()
    suggestion = DeckTagSuggestion.objects.get(normalized_value="transition type")
    accepted = service.accept_suggestion_as_new(suggestion_id=suggestion.id)

    assert accepted is not None
    assert accepted.accepted_tag is not None
    accepted_tag = accepted.accepted_tag

    for transition in (
        lambda: service.accept_suggestion_to_existing(
            suggestion_id=suggestion.id,
            target_id=accepted_tag.id,
        ),
        lambda: service.reject_suggestion(suggestion_id=suggestion.id),
    ):
        try:
            transition()
        except ValueError as exc:
            assert "Only pending deck tag suggestions" in str(exc)
        else:
            raise AssertionError("Resolved deck tag suggestions must not transition again.")

    assert DeckTagAssignment.objects.filter(deck=deck, tag=accepted_tag).count() == 1
    assert service.delete_tag(tag_id=accepted_tag.id) is True
    suggestion.refresh_from_db()
    assert suggestion.status == "rejected"
    assert suggestion.accepted_tag is None

    replacement_suggestion = DeckTagSuggestion.objects.create(
        display_value="Moved Type",
        normalized_value="moved type",
    )
    replacement_tag = service.create_tag(kind="type", label="Moved Type")
    service.accept_suggestion_to_existing(
        suggestion_id=replacement_suggestion.id,
        target_id=replacement_tag.id,
    )
    service.update_tag(tag_id=replacement_tag.id, kind="role")
    replacement_suggestion.refresh_from_db()
    assert replacement_suggestion.status == "rejected"
    assert replacement_suggestion.accepted_tag is None


def test_public_and_owned_deck_lists_filter_deck_tags_with_any_and_all_matching() -> None:
    owner = _create_user("deck-tag-filter-owner", "password")
    hero = _create_card(name="Deck Tag Filter Hero", hero=True)
    cards = _build_mainboard_cards()
    role = DeckTag.objects.get(kind="role", key="control")
    type_tag = DeckTagService().create_tag(kind="type", label="Filter Test Type")

    both_deck = DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Both Deck Tags",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in cards],
        sideboards=[],
        tag_ids=[role.id, type_tag.id],
    )
    role_deck = DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Role Deck Tag",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in cards],
        sideboards=[],
        tag_ids=[role.id],
    )

    any_response = Client(HTTP_HOST="localhost").get(
        "/decks",
        {"view": "summary", "deck_tag_ids": [role.id, type_tag.id], "deck_tag_match": "any"},
    )
    all_response = Client(HTTP_HOST="localhost").get(
        "/decks",
        {"view": "summary", "deck_tag_ids": [role.id, type_tag.id], "deck_tag_match": "all"},
    )
    owner_client = Client(HTTP_HOST="localhost")
    owner_client.force_login(owner)
    owned_response = owner_client.get(
        "/my/decks",
        {"view": "summary", "deck_tag_ids": [type_tag.id], "deck_tag_match": "any"},
    )
    excluded_response = Client(HTTP_HOST="localhost").get(
        "/decks",
        {"view": "summary", "deck_tag_exclude_ids": [type_tag.id]},
    )
    mixed_response = Client(HTTP_HOST="localhost").get(
        "/decks",
        {
            "deck_tag_ids": [role.id],
            "deck_tag_match": "all",
            "deck_tag_exclude_ids": [type_tag.id],
        },
    )
    owned_excluded_response = owner_client.get(
        "/my/decks",
        {"deck_tag_exclude_ids": [type_tag.id]},
    )

    assert any_response.status_code == 200
    assert all_response.status_code == 200
    assert owned_response.status_code == 200
    assert excluded_response.status_code == 200
    assert mixed_response.status_code == 200
    assert owned_excluded_response.status_code == 200
    assert {row["id"] for row in any_response.json()} >= {both_deck.id, role_deck.id}
    assert [row["id"] for row in all_response.json()] == [both_deck.id]
    assert [row["id"] for row in owned_response.json()] == [both_deck.id]
    assert role_deck.id in {row["id"] for row in excluded_response.json()}
    assert both_deck.id not in {row["id"] for row in excluded_response.json()}
    assert role_deck.id in {row["id"] for row in mixed_response.json()}
    assert both_deck.id not in {row["id"] for row in mixed_response.json()}
    assert [row["id"] for row in owned_excluded_response.json()] == [role_deck.id]

    detail = DeckTagService().get_tag_detail(tag_id=type_tag.id)
    assert detail is not None
    assert detail["linked_deck_count"] == 1
    assert DeckTagService().delete_tag(tag_id=type_tag.id) is True
    assert not DeckTagAssignment.objects.filter(deck=both_deck, tag_id=type_tag.id).exists()

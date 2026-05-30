from __future__ import annotations

from collections.abc import Iterable
from itertools import count

from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from card_reader_core.models import (
    Card,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Deck,
    Keyword,
    ParseResult,
    Symbol,
    Tag,
    Template,
    Type,
)
from card_reader_core.config.settings import settings
from card_reader_core.storage import build_storage_relative_path
from card_reader_core.services.decks import DeckEntryInput, DeckService, DeckSideboardInput

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
    is_hero: bool,
    type_labels: list[str] | None = None,
    lifecycle_status: str = "active",
    deck_building_config: dict[str, object] | None = None,
) -> Card:
    template = _ensure_template()
    unique_name = f"{name} {next(_CARD_NAME_COUNTER)}"
    card = Card.objects.create(
        key=unique_name.lower().replace(" ", "-"),
        label=unique_name,
        is_hero=is_hero,
        lifecycle_status=lifecycle_status,
        deck_building_config_json=deck_building_config or {},
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
        cards.append(_create_card(name=f"Mainboard Card {index}", is_hero=False, type_labels=type_labels))
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
    assert payload["example_config"]["overrides"]["mainboard_copy_limit"]["max"] == 6
    assert payload["example_config"]["overrides"]["legendary_copy_limit"]["scope"] == "whole_deck"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_excludes_private_decks() -> None:
    owner = _create_user("deck-public-owner", "password")
    hero = _create_card(name="Public Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_excludes_invalid_public_decks() -> None:
    owner = _create_user("deck-invalid-public-owner", "password")
    hero = _create_card(name="Draft Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_excludes_decks_with_deprecated_cards_but_owner_can_view_warning() -> None:
    owner = _create_user("deck-deprecated-card-owner", "password")
    hero = _create_card(name="Deprecated Warning Hero", is_hero=True)
    deprecated_card = _create_card(
        name="Deprecated Mainboard Card",
        is_hero=False,
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_includes_valid_20_card_public_decks() -> None:
    owner = _create_user("deck-minimum-public-owner", "password")
    hero = _create_card(name="Minimum Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_filters_by_hero_name() -> None:
    owner = _create_user("deck-filter-hero-owner", "password")
    target_hero = _create_card(name="Aurora Captain", is_hero=True)
    other_hero = _create_card(name="Shadow Caller", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_filters_by_author_username() -> None:
    target_owner = _create_user("deck-author-target", "password")
    other_owner = _create_user("deck-author-other", "password")
    hero = _create_card(name="Author Filter Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_filters_by_mainboard_card_name() -> None:
    owner = _create_user("deck-filter-mainboard-owner", "password")
    hero = _create_card(name="Mainboard Hero", is_hero=True)
    featured_card = _create_card(name="Sun Spear", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_filters_by_sideboard_card_name() -> None:
    owner = _create_user("deck-filter-sideboard-owner", "password")
    hero = _create_card(name="Sideboard Filter Hero", is_hero=True)
    sideboard_card = _create_card(name="Moon Trap", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_combines_hero_and_card_filters_with_and() -> None:
    owner = _create_user("deck-filter-and-owner", "password")
    matching_hero = _create_card(name="Ember Warden", is_hero=True)
    non_matching_hero = _create_card(name="Frost Sage", is_hero=True)
    featured_card = _create_card(name="Solar Flare", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_filters_by_affinity_symbols_with_any_match() -> None:
    owner = _create_user("deck-filter-affinity-any-owner", "password")
    hero = _create_card(name="Affinity Any Hero", is_hero=True)
    fire_card = _create_card(name="Firecard", is_hero=False)
    water_card = _create_card(name="Watercard", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_filters_by_affinity_symbols_with_all_match() -> None:
    owner = _create_user("deck-filter-affinity-all-owner", "password")
    hero = _create_card(name="Affinity All Hero", is_hero=True)
    dual_card = _create_card(name="Dual Affinity Card", is_hero=False)
    fire_only_card = _create_card(name="Fire Only Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_filters_by_affinity_symbol_exclusions() -> None:
    owner = _create_user("deck-filter-affinity-exclude-owner", "password")
    hero = _create_card(name="Affinity Exclude Hero", is_hero=True)
    fire_card = _create_card(name="Exclude Fire Card", is_hero=False)
    water_card = _create_card(name="Exclude Water Card", is_hero=False)
    dual_card = _create_card(name="Exclude Dual Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_list_filters_still_exclude_private_and_invalid_decks() -> None:
    owner = _create_user("deck-filter-visibility-owner", "password")
    target_hero = _create_card(name="Visible Filter Hero", is_hero=True)
    private_hero = _create_card(name="Hidden Filter Hero", is_hero=True)
    invalid_hero = _create_card(name="Draft Filter Hero", is_hero=True)
    featured_card = _create_card(name="Comet Blade", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_payload_includes_card_types() -> None:
    owner = _create_user("deck-types-owner", "password")
    hero = _create_card(name="Typed Hero", is_hero=True, type_labels=["Hero", "Mage"])
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_payload_includes_tooltip_metadata() -> None:
    owner = _create_user("deck-tooltip-owner", "password")
    hero = _create_card(name="Tooltip Hero", is_hero=True)
    card = _create_card(name="Tooltip Card", is_hero=False, type_labels=["Equipment", "Amulet"])
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_payload_uses_immutable_card_image_urls() -> None:
    owner = _create_user("deck-image-owner", "password")
    hero = _create_card(name="Image Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_detail_hides_private_decks_from_non_owners() -> None:
    owner = _create_user("deck-private-owner", "password")
    hero = _create_card(name="Private Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_public_deck_detail_allows_unlisted_decks_for_guests() -> None:
    owner = _create_user("deck-unlisted-owner", "password")
    hero = _create_card(name="Unlisted Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_owner_deck_list_filters_owned_decks_by_card_name_without_leaking_other_users_decks() -> None:
    owner = _create_user("deck-owner-filter-user", "password")
    other_owner = _create_user("deck-owner-filter-other-user", "password")
    hero = _create_card(name="Owner Filter Hero", is_hero=True)
    featured_card = _create_card(name="Owner Filter Blade", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_owner_deck_list_ignores_public_author_filter() -> None:
    owner = _create_user("deck-owner-author-filter-user", "password")
    other_owner = _create_user("deck-owner-author-filter-other", "password")
    hero = _create_card(name="Owner Author Filter Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_owner_deck_list_filters_owned_decks_by_affinity_symbol() -> None:
    owner = _create_user("deck-owner-affinity-filter-user", "password")
    hero = _create_card(name="Owner Affinity Hero", is_hero=True)
    fire_card = _create_card(name="Owner Fire Card", is_hero=False)
    water_card = _create_card(name="Owner Water Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_payload_includes_sideboards_and_aggregate_totals() -> None:
    owner = _create_user("deck-sideboard-owner", "password")
    hero = _create_card(name="Sideboard Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Sideboard Card", is_hero=False)
    extra_sideboard_card = _create_card(name="Second Sideboard Card", is_hero=False)

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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_authenticated_owner_can_create_deck_with_sideboards() -> None:
    username = "deck-sideboard-crud-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard CRUD Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="CRUD Sideboard Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_patch_preserves_sideboards_when_omitted() -> None:
    username = "deck-patch-preserve-sideboards-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Patch Preserve Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Patch Preserve Sideboard Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_patch_clears_sideboards_when_explicitly_empty() -> None:
    username = "deck-patch-clear-sideboards-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Patch Clear Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Patch Clear Sideboard Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_patch_preserves_mainboard_when_entries_omitted() -> None:
    username = "deck-patch-preserve-entries-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Patch Preserve Entries Hero", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_sideboard_name_is_required() -> None:
    username = "deck-sideboard-name-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard Name Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Nameless Sideboard Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_sideboards_reject_hero_cards() -> None:
    username = "deck-sideboard-hero-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard Hero Reject", is_hero=True)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_sideboards_reject_quantities_above_100() -> None:
    username = "deck-sideboard-quantity-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard Quantity Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Large Sideboard Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_create_warns_for_multiple_legendary_mainboard_copies() -> None:
    username = "deck-legendary-mainboard-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Legendary Limit Hero", is_hero=True)
    legendary_card = _create_card(name="Legendary Mainboard Card", is_hero=False, type_labels=["Legendary"])
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_update_uses_legendary_scope_for_warnings() -> None:
    username = "deck-legendary-sideboard-user"
    password = "password"
    owner = _create_user(username, password)
    hero = _create_card(
        name="Legendary Sideboard Hero",
        is_hero=True,
        deck_building_config={
            "overrides": {
                "legendary_copy_limit": {
                    "scope": "whole_deck",
                }
            }
        },
    )
    legendary_card = _create_card(name="Legendary Sideboard Card", is_hero=False, type_labels=["Legendary"])
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_create_allows_one_legendary_copy_and_large_non_legendary_sideboard() -> None:
    username = "deck-legendary-valid-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Valid Legendary Hero", is_hero=True)
    legendary_card = _create_card(name="Valid Legendary Card", is_hero=False, type_labels=["Legendary"])
    sideboard_card = _create_card(name="Valid Large Sideboard Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_create_rejects_non_legendary_mainboard_copies_above_four() -> None:
    username = "deck-mainboard-limit-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Mainboard Limit Hero", is_hero=True)
    limited_card = _create_card(name="Mainboard Limited Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_hero_override_allows_six_mainboard_copies() -> None:
    username = "deck-mainboard-override-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(
        name="Mainboard Override Hero",
        is_hero=True,
        deck_building_config={
            "overrides": {
                "mainboard_copy_limit": {
                    "max": 6,
                }
            }
        },
    )
    limited_card = _create_card(name="Mainboard Six Copy Card", is_hero=False)
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_sideboards_reject_duplicate_cards_within_same_sideboard() -> None:
    username = "deck-sideboard-duplicate-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Sideboard Duplicate Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    sideboard_card = _create_card(name="Duplicate Sideboard Card", is_hero=False)
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
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    csrf_token = _login_and_get_csrf_token(client, other_user.username, "password")

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
            "visibility": "private",
            "hero_card_id": non_hero.id,
            "entries": _valid_entries(mainboard_cards),
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Hero card must be marked as a hero."


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_create_allows_invalid_in_progress_drafts_below_minimum_card_count() -> None:
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_deck_create_marks_deck_invalid_without_enough_mana_type_cards() -> None:
    username = "deck-invalid-mana-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(name="Mana Count Hero", is_hero=True)
    non_mana_cards = [_create_card(name=f"Non Mana Card {index}", is_hero=False) for index in range(20)]
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_hero_override_allows_deck_without_mana_type_cards() -> None:
    username = "deck-mana-override-user"
    password = "password"
    _create_user(username, password)
    hero = _create_card(
        name="Mana Override Hero",
        is_hero=True,
        deck_building_config={
            "overrides": {
                "mana_type_count": {
                    "min": 0,
                }
            }
        },
    )
    non_mana_cards = [_create_card(name=f"Override Non Mana Card {index}", is_hero=False) for index in range(20)]
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
def test_cards_list_hides_deprecated_cards_by_default_but_can_include_them() -> None:
    active_card = _create_card(name="Active Lifecycle Card", is_hero=False)
    deprecated_card = _create_card(
        name="Deprecated Lifecycle Card",
        is_hero=False,
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


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_latest_version_patch_can_deprecate_card() -> None:
    username = "deck-card-lifecycle-toggle-user"
    password = "password"
    _create_user(username, password, is_staff=True)
    card = _create_card(name="Toggle Lifecycle Card", is_hero=False)
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

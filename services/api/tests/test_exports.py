from __future__ import annotations

import base64
from io import BytesIO
import json
from itertools import count

from django.test import Client
from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    Card,
    CardBack,
    CardVersion,
    CardVersionImage,
    ContentVersion,
    DeckTag,
    TtsCardSheet,
)
from card_reader_core.storage import build_storage_relative_path
from card_reader_core.services.decks import DeckEntryInput, DeckService, DeckSideboardInput
from test_decks import _build_mainboard_cards, _create_card, _create_user, _login_and_get_csrf_token

_CONTENT_VERSION_COUNTER = count(500)


def test_public_deck_tts_export_returns_sheet_payload_with_metadata() -> None:
    TtsCardSheet.objects.all().delete()
    owner = _create_user("tts-export-public-owner", "password")
    hero = _create_card(name="TTS Export Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    tag = DeckTag.objects.create(kind="role", key="tts-control", label="TTS Control")
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Deck",
        description="Export me",
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
        difficulty="hard",
        tag_ids=[tag.id],
    )
    _prepare_tts_export("public-deck", [hero, *mainboard_cards])

    response = Client(HTTP_HOST="cards.example").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["exported_count"] == 1 + (4 * len(mainboard_cards))
    assert response_payload["skipped_count"] == 0
    assert response_payload["sheet_count"] == 1
    payload = _decode_tts_card_export(response_payload["encoded_payload"])
    assert payload["schema"] == "card-reader.tts-cards.v2"
    assert payload["collection"] == {
        "name": "TTS Export Deck",
        "description": "Export me",
        "source": {
            "type": "deck",
            "deck_id": deck.id,
            "scope": "mainboard",
            "hero_card_id": hero.id,
            "difficulty": "hard",
            "tags": [
                {
                    "id": tag.id,
                    "key": "tts-control",
                    "label": "TTS Control",
                    "kind": "role",
                }
            ],
        },
    }
    assert payload["cards"][0]["card_id"] == hero.id
    assert payload["cards"][0]["role"] == "hero"
    assert [card["card_id"] for card in payload["cards"][1:]] == [
        card.id for card in mainboard_cards
    ]
    assert all(card["role"] == "mainboard" for card in payload["cards"][1:])
    assert all(card["quantity"] == 4 for card in payload["cards"][1:])
    assert payload["sheets"][0]["face_url"].startswith("http://cards.example/tts/card-sheets/")


def test_private_deck_tts_export_is_hidden_from_non_owner_but_visible_to_owner() -> None:
    TtsCardSheet.objects.all().delete()
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
    _prepare_tts_export("private-deck", [hero, *mainboard_cards])

    public_response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    owner_client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
    _login_and_get_csrf_token(owner_client, owner.username, "password")
    owner_response = owner_client.get(f"/decks/{deck.id}/exports/tts")

    assert public_response.status_code == 404
    assert owner_response.status_code == 200


def test_unlisted_deck_tts_export_is_visible_to_non_owner_by_link() -> None:
    TtsCardSheet.objects.all().delete()
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
    _prepare_tts_export("unlisted-deck", [hero, *mainboard_cards])

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200


def test_main_deck_tts_export_omits_sideboard_entries() -> None:
    TtsCardSheet.objects.all().delete()
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
    _prepare_tts_export("mainboard-only", [hero, *mainboard_cards])

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    payload = _decode_tts_card_export(response.json()["encoded_payload"])
    assert [card["card_id"] for card in payload["cards"]] == [
        hero.id,
        *[card.id for card in mainboard_cards],
    ]
    assert sideboard_card.id not in {card["card_id"] for card in payload["cards"]}


def test_tts_export_can_target_one_sideboard() -> None:
    TtsCardSheet.objects.all().delete()
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
    _prepare_tts_export("target-sideboard", [sideboard_card])

    response = Client(HTTP_HOST="localhost").get(
        f"/decks/{deck.id}/exports/tts?sideboard_id={sideboard.id}"
    )

    assert response.status_code == 200
    assert response.json()["exported_count"] == 6
    payload = _decode_tts_card_export(response.json()["encoded_payload"])
    assert payload["collection"] == {
        "name": "TTS Export Targeted Deck - Tech",
        "description": "Sideboard export",
        "source": {
            "type": "deck",
            "deck_id": deck.id,
            "scope": "sideboard",
            "hero_card_id": hero.id,
            "difficulty": None,
            "tags": [],
            "sideboard_id": sideboard.id,
            "sideboard_name": "Tech",
        },
    }
    assert [
        {
            "card_id": card["card_id"],
            "name": card["name"],
            "quantity": card["quantity"],
            "role": card["role"],
        }
        for card in payload["cards"]
    ] == [
        {
            "card_id": sideboard_card.id,
            "name": sideboard_card.latest_version.name,
            "quantity": 6,
            "role": "sideboard",
        }
    ]


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

    response = Client(HTTP_HOST="localhost").get(
        f"/decks/{deck.id}/exports/tts?sideboard_id=missing"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Sideboard not found"


def test_deck_tts_export_reports_skipped_non_hero_quantities() -> None:
    TtsCardSheet.objects.all().delete()
    owner = _create_user("tts-export-skipped-owner", "password")
    hero = _create_card(name="TTS Export Skipped Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    missing = mainboard_cards[0]
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Skipped Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    _prepare_tts_export("skipped-mainboard", [hero, *mainboard_cards[1:]])

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["exported_count"] == 1 + (4 * (len(mainboard_cards) - 1))
    assert response_payload["skipped_count"] == 4
    payload = _decode_tts_card_export(response_payload["encoded_payload"])
    assert payload["skipped"] == [
        {
            "card_id": missing.id,
            "name": missing.latest_version.name,
            "quantity": 4,
            "reason": "Card has no usable latest image.",
            "role": "mainboard",
        }
    ]


def test_deck_tts_export_requires_usable_hero_artwork() -> None:
    TtsCardSheet.objects.all().delete()
    owner = _create_user("tts-export-required-hero-owner", "password")
    hero = _create_card(name="TTS Export Required Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Required Hero Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    _prepare_tts_export("required-hero", mainboard_cards)

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Required deck hero '{hero.latest_version.name}' has no usable latest image."
    )


def test_owned_deck_tts_export_includes_deprecated_referenced_cards() -> None:
    TtsCardSheet.objects.all().delete()
    owner = _create_user("tts-export-deprecated-owner", "password")
    hero = _create_card(name="TTS Export Deprecated Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deprecated = mainboard_cards[0]
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Deprecated Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    deprecated.lifecycle_status = "deprecated"
    deprecated.save(update_fields=["lifecycle_status", "updated_at"])
    _prepare_tts_export("deprecated-deck", [hero, *mainboard_cards])
    client = Client(HTTP_HOST="localhost")
    client.force_login(owner)

    response = client.get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    payload = _decode_tts_card_export(response.json()["encoded_payload"])
    exported = next(card for card in payload["cards"] if card["card_id"] == deprecated.id)
    assert exported["lifecycle_status"] == "deprecated"


def test_deck_tts_export_returns_retryable_pending_sheet_response(monkeypatch) -> None:
    TtsCardSheet.objects.all().delete()
    owner = _create_user("tts-export-pending-owner", "password")
    hero = _create_card(name="TTS Export Pending Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export Pending Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    _prepare_tts_export("pending-deck", [hero, *mainboard_cards])
    monkeypatch.setattr(settings, "environment", "production")

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 503
    assert response["Retry-After"] == "2"


def test_deck_tts_export_requires_a_current_card_back() -> None:
    TtsCardSheet.objects.all().delete()
    CardBack.objects.filter(is_current=True).update(is_current=False)
    owner = _create_user("tts-export-no-back-owner", "password")
    hero = _create_card(name="TTS Export No Back Hero", is_hero=True)
    mainboard_cards = _build_mainboard_cards()
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.id),
        name="TTS Export No Back Deck",
        description=None,
        visibility="public",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=4) for card in mainboard_cards],
        sideboards=[],
    )
    for card in [hero, *mainboard_cards]:
        assert card.latest_version is not None
        _create_card_image(card.latest_version, content=card.id.encode("utf-8"))

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A usable current card back is required before exporting TTS cards."
    )


def test_tts_export_preserves_saved_entry_order() -> None:
    TtsCardSheet.objects.all().delete()
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
    _prepare_tts_export("saved-order", [hero, beta_card, alpha_card, *filler_cards])

    response = Client(HTTP_HOST="localhost").get(f"/decks/{deck.id}/exports/tts")

    assert response.status_code == 200
    payload = _decode_tts_card_export(response.json()["encoded_payload"])
    assert [card["name"] for card in payload["cards"][1:3]] == [
        beta_card.latest_version.name,
        alpha_card.latest_version.name,
    ]


def test_gallery_tts_card_export_uses_all_matching_cards_and_reports_missing_images(
    monkeypatch,
) -> None:
    TtsCardSheet.objects.all().delete()
    staff = _create_user("tts-card-gallery-staff", "password", is_staff=True)
    client = Client(HTTP_HOST="cards.example")
    client.force_login(staff)
    monkeypatch.setattr(settings, "public_api_base_url", "https://cards.example/api")
    _create_current_card_back("gallery")
    beta = _create_card(name="Direct Gallery Beta", is_hero=False)
    alpha = _create_card(name="Direct Gallery Alpha", is_hero=False)
    missing = _create_card(name="Direct Gallery Missing", is_hero=False)
    _create_card_image(beta.latest_version, content=b"beta")
    _create_card_image(alpha.latest_version, content=b"alpha")

    response = client.post(
        "/exports/tts/cards",
        data={
            "source": {
                "type": "gallery",
                "filters": {
                    "q": "Direct Gallery",
                    "sort": "name_asc",
                    "page": 1,
                    "page_size": 1,
                    "show_groups": True,
                },
            }
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["exported_count"] == 2
    assert response_payload["skipped_count"] == 1
    assert response_payload["sheet_count"] == 1
    payload = _decode_tts_card_export(response_payload["encoded_payload"])
    assert payload["schema"] == "card-reader.tts-cards.v2"
    assert payload["collection"]["name"] == "Card Reader Gallery"
    assert payload["collection"]["source"]["filters"]["sort"] == "name_asc"
    assert "page" not in payload["collection"]["source"]["filters"]
    assert [card["name"] for card in payload["cards"]] == [
        alpha.latest_version.name,
        beta.latest_version.name,
    ]
    assert payload["sheets"][0]["face_url"].startswith("https://cards.example/api/tts/card-sheets/")
    assert payload["sheets"][0]["face_url"].endswith("/image.webp")
    assert payload["cards"][0]["sheet_id"] == payload["sheets"][0]["sheet_id"]
    assert {card["slot_index"] for card in payload["cards"]} == {0, 1}
    assert payload["cards"][0]["quantity"] == 1
    assert payload["card_back_url"].startswith("https://cards.example/api/card-images/images/")
    assert payload["skipped"] == [
        {
            "card_id": missing.id,
            "name": missing.latest_version.name,
            "quantity": 1,
            "reason": "Card has no usable latest image.",
        }
    ]


def test_content_version_tts_card_export_deduplicates_identity_and_uses_latest_artwork() -> None:
    TtsCardSheet.objects.all().delete()
    staff = _create_user("tts-card-version-staff", "password", is_staff=True)
    client = Client(HTTP_HOST="cards.example")
    client.force_login(staff)
    _create_current_card_back("content-version")
    content_version = _create_content_version("TTS direct export")
    card = _create_card(name="Content Version Direct Card", is_hero=False)
    historical = card.latest_version
    historical.is_latest = False
    historical.content_version = content_version
    historical.save(update_fields=["is_latest", "content_version", "updated_at"])
    _clone_card_version(
        historical,
        version_number=2,
        is_latest=False,
        content_version=content_version,
        name="Historical duplicate",
    )
    latest = _clone_card_version(
        historical,
        version_number=3,
        is_latest=True,
        content_version=None,
        name="Current latest artwork",
    )
    card.latest_version = latest
    card.save(update_fields=["latest_version", "updated_at"])
    image = _create_card_image(latest, content=b"current")

    response = client.post(
        "/exports/tts/cards",
        data={
            "source": {
                "type": "content_version",
                "content_version_id": content_version.id,
            }
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["exported_count"] == 1
    assert response_payload["skipped_count"] == 0
    assert response_payload["sheet_count"] == 1
    payload = _decode_tts_card_export(response_payload["encoded_payload"])
    assert payload["collection"]["source"] == {
        "type": "content_version",
        "content_version_id": content_version.id,
        "version_number": content_version.version_number,
    }
    assert payload["cards"] == [
        {
            "card_id": card.id,
            "card_version_id": latest.id,
            "name": latest.name,
            "quantity": 1,
            "image_checksum": image.checksum,
            "sheet_id": payload["sheets"][0]["sheet_id"],
            "slot_index": 0,
            "lifecycle_status": "active",
        }
    ]


def test_content_version_tts_card_export_excludes_deprecated_card_identities() -> None:
    TtsCardSheet.objects.all().delete()
    staff = _create_user("tts-card-version-active-staff", "password", is_staff=True)
    client = Client(HTTP_HOST="cards.example")
    client.force_login(staff)
    _create_current_card_back("content-version-active")
    content_version = _create_content_version("TTS active-only direct export")
    active = _create_card(name="Content Version Active Card", is_hero=False)
    deprecated = _create_card(name="Content Version Deprecated Card", is_hero=False)
    active.latest_version.content_version = content_version
    active.latest_version.save(update_fields=["content_version", "updated_at"])
    deprecated.latest_version.content_version = content_version
    deprecated.latest_version.save(update_fields=["content_version", "updated_at"])
    deprecated.lifecycle_status = "deprecated"
    deprecated.save(update_fields=["lifecycle_status", "updated_at"])
    _create_card_image(active.latest_version, content=b"active")
    _create_card_image(deprecated.latest_version, content=b"deprecated")

    response = client.post(
        "/exports/tts/cards",
        data={
            "source": {
                "type": "content_version",
                "content_version_id": content_version.id,
            }
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["exported_count"] == 1
    assert response_payload["skipped_count"] == 0
    payload = _decode_tts_card_export(response_payload["encoded_payload"])
    assert [card["card_id"] for card in payload["cards"]] == [active.id]
    assert payload["skipped"] == []


def test_tts_card_export_requires_staff_and_a_current_card_back() -> None:
    regular = _create_user("tts-card-regular", "password", is_staff=False)
    regular_client = Client(HTTP_HOST="cards.example")
    regular_client.force_login(regular)
    request_payload = {"source": {"type": "gallery", "filters": {"q": "nothing"}}}

    assert Client(HTTP_HOST="cards.example").post(
        "/exports/tts/cards",
        data=request_payload,
        content_type="application/json",
    ).status_code in {401, 403}
    assert (
        regular_client.post(
            "/exports/tts/cards",
            data=request_payload,
            content_type="application/json",
        ).status_code
        == 403
    )

    CardBack.objects.filter(is_current=True).update(is_current=False)
    staff = _create_user("tts-card-no-back-staff", "password", is_staff=True)
    staff_client = Client(HTTP_HOST="cards.example")
    staff_client.force_login(staff)
    response = staff_client.post(
        "/exports/tts/cards",
        data=request_payload,
        content_type="application/json",
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A usable current card back is required before exporting TTS cards."
    )


def test_tts_card_export_rejects_a_selection_without_usable_images() -> None:
    staff = _create_user("tts-card-empty-staff", "password", is_staff=True)
    client = Client(HTTP_HOST="cards.example")
    client.force_login(staff)
    _create_current_card_back("empty-selection")
    _create_card(name="TTS Empty Selection Card", is_hero=False)

    response = client.post(
        "/exports/tts/cards",
        data={"source": {"type": "gallery", "filters": {"q": "TTS Empty Selection Card"}}},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No cards with usable latest images matched this export."


def _decode_tts_card_export(encoded_payload: str) -> dict[str, object]:
    return json.loads(base64.b64decode(encoded_payload).decode("utf-8"))


def _prepare_tts_export(label: str, cards: list[Card]) -> None:
    _create_current_card_back(label)
    for card in cards:
        assert card.latest_version is not None
        _create_card_image(card.latest_version, content=f"{label}-{card.id}".encode("utf-8"))


def _create_current_card_back(label: str) -> CardBack:
    CardBack.objects.filter(is_current=True).update(is_current=False)
    stored_path = build_storage_relative_path("images", f"tts-card-back-{label}.webp")
    path = settings.storage_root_dir / stored_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"card-back")
    return CardBack.objects.create(
        label=f"TTS {label}",
        original_filename=f"{label}.png",
        source_file=f"uploads/card-backs/{label}.png",
        stored_path=stored_path,
        width=63,
        height=88,
        checksum=f"card-back-{label}",
        is_current=True,
    )


def _create_card_image(version: CardVersion, *, content: bytes) -> CardVersionImage:
    stored_path = build_storage_relative_path("images", f"tts-card-{version.id}.webp")
    path = settings.storage_root_dir / stored_path
    path.parent.mkdir(parents=True, exist_ok=True)
    color = tuple((content[index % len(content)] if content else 0) for index in range(3))
    buffer = BytesIO()
    Image.new("RGB", (50, 70), color).save(buffer, format="WEBP")
    path.write_bytes(buffer.getvalue())
    return CardVersionImage.objects.create(
        card_version=version,
        source_file=stored_path,
        stored_path=stored_path,
        checksum=f"checksum-{version.id}",
    )


def _create_content_version(description: str) -> ContentVersion:
    patch = next(_CONTENT_VERSION_COUNTER)
    return ContentVersion.objects.create(
        version_number=f"99.0.{patch}",
        base_version="99.0",
        major=99,
        minor=0,
        patch=patch,
        description=description,
    )


def _clone_card_version(
    source: CardVersion,
    *,
    version_number: int,
    is_latest: bool,
    content_version: ContentVersion | None,
    name: str,
) -> CardVersion:
    return CardVersion.objects.create(
        card=source.card,
        version_number=version_number,
        template=source.template,
        image_hash=f"{source.image_hash}-{version_number}",
        name=name,
        type_line=source.type_line,
        mana_cost=source.mana_cost,
        mana_symbols_json=source.mana_symbols_json,
        mana_value=source.mana_value,
        rules_text_raw=source.rules_text_raw,
        rules_text_enriched=source.rules_text_enriched,
        rules_text=source.rules_text,
        confidence=source.confidence,
        field_sources_json=source.field_sources_json,
        parsed_snapshot_json=source.parsed_snapshot_json,
        is_latest=is_latest,
        previous_version=source,
        content_version=content_version,
    )

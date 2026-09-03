from pathlib import Path
from typing import Any

import pytest
from django.db.models.deletion import ProtectedError
from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    Card,
    CardBack,
    CardFactionAssignment,
    CardRoleAssignment,
)
from card_reader_core.services.card_backs import (
    clear_faction_default,
    clear_pool_default,
    clear_role_default,
    get_faction_card_back_defaults,
    get_pool_card_back_defaults,
    get_role_card_back_defaults,
    resolve_effective_card_backs,
    select_card_back_override,
    set_faction_default,
    set_pool_default,
    set_role_default,
)
from card_reader_core.services.card_merges import merge_cards, preview_card_merge


@pytest.mark.django_db
def test_resolution_prefers_override_and_uses_bounded_queries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    django_assert_num_queries: Any,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    player_default = _create_usable_card_back("player-default")
    override = _create_usable_card_back("override")
    set_pool_default("player", player_default.id)
    inherited = Card.objects.create(key="inherited", label="Inherited", card_pool="player")
    overridden = Card.objects.create(
        key="overridden",
        label="Overridden",
        card_pool="player",
        card_back_override=override,
    )

    with django_assert_num_queries(6):
        resolved = resolve_effective_card_backs([inherited.id, overridden.id])

    assert resolved[inherited.id].source == "pool_default"
    assert resolved[inherited.id].card_back == player_default
    assert resolved[overridden.id].source == "override"
    assert resolved[overridden.id].card_back == override


@pytest.mark.django_db
def test_role_defaults_apply_across_pools_and_precede_evil_factions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    player_default = _create_usable_card_back("player-default")
    evil_default = _create_usable_card_back("evil-default")
    faction_default = _create_usable_card_back("order-default")
    hero_default = _create_usable_card_back("hero-default")
    event_default = _create_usable_card_back("event-default")
    set_pool_default("player", player_default.id)
    set_pool_default("evil", evil_default.id)
    set_faction_default("order", faction_default.id)
    set_role_default("hero", hero_default.id)
    set_role_default("event", event_default.id)
    player_card = Card.objects.create(key="player-event", label="Player Event")
    evil_card = Card.objects.create(key="evil-multi-role", label="Evil Multi Role", card_pool="evil")
    CardRoleAssignment.objects.create(card=player_card, role="event")
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card=evil_card, role="event"),
            CardRoleAssignment(card=evil_card, role="hero"),
            CardRoleAssignment(card=evil_card, role="boss"),
        ]
    )
    CardFactionAssignment.objects.create(card=evil_card, faction="order")

    resolved = resolve_effective_card_backs([player_card.id, evil_card.id])

    assert resolved[player_card.id].source == "role_default"
    assert resolved[player_card.id].role == "event"
    assert resolved[player_card.id].faction is None
    assert resolved[player_card.id].card_back == event_default
    assert resolved[evil_card.id].source == "role_default"
    assert resolved[evil_card.id].role == "hero"
    assert resolved[evil_card.id].faction is None
    assert resolved[evil_card.id].card_back == hero_default


@pytest.mark.django_db
def test_evil_faction_defaults_precede_pool_default_in_canonical_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    evil_default = _create_usable_card_back("evil-default")
    order_default = _create_usable_card_back("order-default")
    blood_default = _create_usable_card_back("blood-default")
    set_pool_default("evil", evil_default.id)
    set_faction_default("order", order_default.id)
    set_faction_default("blood", blood_default.id)
    order_and_blood = Card.objects.create(
        key="order-and-blood",
        label="Order and Blood",
        card_pool="evil",
    )
    CardFactionAssignment.objects.bulk_create(
        [
            CardFactionAssignment(card=order_and_blood, faction="blood"),
            CardFactionAssignment(card=order_and_blood, faction="order"),
        ]
    )
    no_faction = Card.objects.create(
        key="no-faction",
        label="No Faction",
        card_pool="evil",
    )

    resolved = resolve_effective_card_backs([order_and_blood.id, no_faction.id])

    assert resolved[order_and_blood.id].source == "faction_default"
    assert resolved[order_and_blood.id].faction == "order"
    assert resolved[order_and_blood.id].card_back == order_default
    assert resolved[no_faction.id].source == "pool_default"
    assert resolved[no_faction.id].faction is None
    assert resolved[no_faction.id].card_back == evil_default


@pytest.mark.django_db
def test_faction_defaults_only_apply_inside_evil_pool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    player_default = _create_usable_card_back("player-default")
    order_default = _create_usable_card_back("order-default")
    set_pool_default("player", player_default.id)
    set_faction_default("order", order_default.id)
    player_card = Card.objects.create(
        key="player-order",
        label="Player Order",
        card_pool="player",
    )
    CardFactionAssignment.objects.create(card=player_card, faction="order")

    resolved = resolve_effective_card_backs([player_card.id])[player_card.id]

    assert resolved.source == "pool_default"
    assert resolved.faction is None
    assert resolved.card_back == player_default


@pytest.mark.django_db
def test_pool_change_keeps_override_and_changes_inheritance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    player_default = _create_usable_card_back("player-default")
    evil_default = _create_usable_card_back("evil-default")
    override = _create_usable_card_back("override")
    set_pool_default("player", player_default.id)
    set_pool_default("evil", evil_default.id)
    inherited = Card.objects.create(key="inherited", label="Inherited", card_pool="player")
    overridden = Card.objects.create(
        key="overridden",
        label="Overridden",
        card_pool="player",
        card_back_override=override,
    )

    inherited.card_pool = "evil"
    inherited.save(update_fields=["card_pool"])
    overridden.card_pool = "evil"
    overridden.save(update_fields=["card_pool"])
    resolved = resolve_effective_card_backs([inherited.id, overridden.id])

    assert resolved[inherited.id].card_back == evil_default
    assert resolved[overridden.id].card_back == override


@pytest.mark.django_db
def test_assignments_validate_files_and_protect_referenced_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    usable = _create_usable_card_back("usable")
    missing = CardBack.objects.create(
        label="Missing",
        original_filename="missing.png",
        source_file="uploads/missing.png",
        stored_path="images/missing.webp",
        width=63,
        height=88,
        checksum="missing",
    )

    assert select_card_back_override(usable.id) == usable
    assert select_card_back_override(None) is None
    with pytest.raises(ValueError, match="missing"):
        set_pool_default("evil", missing.id)
    with pytest.raises(ValueError, match="missing"):
        set_faction_default("order", missing.id)
    with pytest.raises(ValueError, match="missing"):
        set_role_default("hero", missing.id)
    set_pool_default("evil", usable.id)
    with pytest.raises(ProtectedError):
        usable.delete()
    override = _create_usable_card_back("protected-override")
    Card.objects.create(key="protected-override", label="Protected", card_back_override=override)
    with pytest.raises(ProtectedError):
        override.delete()


@pytest.mark.django_db
def test_defaults_explicitly_include_missing_pools() -> None:
    assert get_pool_card_back_defaults() == {
        "player": None,
        "evil": None,
        "neutral": None,
    }


@pytest.mark.django_db
def test_defaults_explicitly_include_missing_factions() -> None:
    assert get_faction_card_back_defaults() == {
        "order": None,
        "blood": None,
        "dark": None,
        "metal": None,
        "fire": None,
    }


@pytest.mark.django_db
def test_defaults_explicitly_include_missing_roles() -> None:
    assert get_role_card_back_defaults() == {
        "hero": None,
        "boss": None,
        "location": None,
        "boon": None,
        "event": None,
        "shop_item": None,
        "directive": None,
        "reminder": None,
        "mana": None,
    }


@pytest.mark.django_db
def test_pool_default_can_be_cleared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    card_back = _create_usable_card_back("default")
    set_pool_default("player", card_back.id)

    clear_pool_default("player")

    assert get_pool_card_back_defaults()["player"] is None


@pytest.mark.django_db
def test_faction_default_can_be_cleared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    card_back = _create_usable_card_back("faction-default")
    set_faction_default("dark", card_back.id)

    clear_faction_default("dark")

    assert get_faction_card_back_defaults()["dark"] is None


@pytest.mark.django_db
def test_role_default_can_be_cleared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    card_back = _create_usable_card_back("role-default")
    set_role_default("location", card_back.id)

    clear_role_default("location")

    assert get_role_card_back_defaults()["location"] is None


@pytest.mark.django_db
def test_merge_warns_about_different_overrides_and_preserves_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    target_back = _create_usable_card_back("merge-target")
    source_back = _create_usable_card_back("merge-source")
    target = Card.objects.create(
        key="merge-target",
        label="Merge Target",
        card_back_override=target_back,
    )
    source = Card.objects.create(
        key="merge-source",
        label="Merge Source",
        card_back_override=source_back,
    )

    preview = preview_card_merge(target_card_id=target.id, source_card_ids=[source.id])
    merge_cards(target_card_id=target.id, source_card_ids=[source.id])

    assert preview.warnings == [
        "Card-back overrides differ; the target Card's override will be preserved.",
    ]
    target.refresh_from_db()
    assert target.card_back_override_id == target_back.id


def _create_usable_card_back(label: str) -> CardBack:
    stored_path = f"images/{label}.webp"
    path = settings.storage_root_dir / stored_path
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (63, 88), color=(20, 40, 90)).save(path, format="WEBP")
    return CardBack.objects.create(
        label=label,
        original_filename=f"{label}.png",
        source_file=f"uploads/{label}.png",
        stored_path=stored_path,
        width=63,
        height=88,
        checksum=label,
    )

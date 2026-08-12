from __future__ import annotations

import pytest
from django.core.management import call_command
from django.db import IntegrityError

from card_reader_core.models import Card, CardAlias, CardIdentityPoolLock
from card_reader_core.repositories.cards import (
    CardIdentityConflict,
    change_card_identity,
    create_card_identity,
    ensure_card_alias,
    resolve_card_by_name_key,
)


def test_card_identity_is_independent_across_all_three_pools() -> None:
    player, player_created = create_card_identity(name="Shared Name", card_pool="player")
    evil, evil_created = create_card_identity(name="Shared Name", card_pool="evil")
    neutral, neutral_created = create_card_identity(name="Shared Name", card_pool="neutral")

    assert player_created and evil_created and neutral_created
    assert len({player.id, evil.id, neutral.id}) == 3
    assert resolve_card_by_name_key(name="Shared Name", card_pool="player") == player
    assert resolve_card_by_name_key(name="Shared Name", card_pool="evil") == evil
    assert resolve_card_by_name_key(name="Shared Name", card_pool="neutral") == neutral


def test_aliases_resolve_per_pool_and_conflict_only_inside_their_pool() -> None:
    player = Card.objects.create(key="player-card", label="Player Card", card_pool="player")
    evil = Card.objects.create(key="evil-card", label="Evil Card", card_pool="evil")
    player_alias = ensure_card_alias(card=player, key="shared-alias", label="Shared Alias")
    evil_alias = ensure_card_alias(card=evil, key="shared-alias", label="Shared Alias")

    assert player_alias is not None and player_alias.card_pool == "player"
    assert evil_alias is not None and evil_alias.card_pool == "evil"
    assert resolve_card_by_name_key(name="shared-alias", card_pool="player") == player
    assert resolve_card_by_name_key(name="shared-alias", card_pool="evil") == evil

    blocker = Card.objects.create(key="blocked", label="Blocked", card_pool="player")
    with pytest.raises(CardIdentityConflict, match="already used"):
        ensure_card_alias(card=blocker, key="shared-alias", label="Blocked Alias")


def test_primary_and_alias_mutations_share_the_pool_lock() -> None:
    initial_revision = CardIdentityPoolLock.objects.get(card_pool="player").revision

    card, created = create_card_identity(name="Serialized Card", card_pool="player")
    ensure_card_alias(card=card, key="serialized-alias", label="Serialized Alias")

    assert created is True
    assert CardIdentityPoolLock.objects.get(card_pool="player").revision == initial_revision + 2


@pytest.mark.django_db(transaction=True)
def test_pool_lock_rows_are_restored_after_database_flush() -> None:
    call_command("flush", verbosity=0, interactive=False)

    assert set(CardIdentityPoolLock.objects.values_list("card_pool", flat=True)) == {
        "player",
        "evil",
        "neutral",
    }


def test_simultaneous_rename_and_pool_move_moves_alias_namespace_atomically() -> None:
    card = Card.objects.create(key="old-name", label="Old Name", card_pool="player")
    CardAlias.objects.create(
        card=card,
        card_pool="player",
        key="older-name",
        label="Older Name",
    )

    change_card_identity(card=card, label="New Name", card_pool="neutral")

    card.refresh_from_db()
    assert (card.key, card.label, card.card_pool) == ("new-name", "New Name", "neutral")
    assert set(card.aliases.values_list("card_pool", "key")) == {
        ("neutral", "old-name"),
        ("neutral", "older-name"),
    }


def test_pool_move_rolls_back_when_destination_namespace_conflicts() -> None:
    moving = Card.objects.create(key="moving", label="Moving", card_pool="player")
    CardAlias.objects.create(
        card=moving,
        card_pool="player",
        key="moving-alias",
        label="Moving Alias",
    )
    Card.objects.create(key="moving", label="Destination Blocker", card_pool="evil")

    with pytest.raises(CardIdentityConflict, match="conflicts"):
        change_card_identity(card=moving, label="Moving", card_pool="evil")

    moving.refresh_from_db()
    assert moving.card_pool == "player"
    assert set(moving.aliases.values_list("card_pool", "key")) == {("player", "moving-alias")}


def test_identity_move_translates_constraint_races_to_domain_conflicts(monkeypatch: pytest.MonkeyPatch) -> None:
    moving = Card.objects.create(key="race-source", label="Race Source", card_pool="player")
    original_save = Card.save

    def raise_identity_race(card: Card, *args: object, **kwargs: object) -> None:
        update_fields = kwargs.get("update_fields")
        if card.id == moving.id and update_fields is not None and "key" in update_fields:
            raise IntegrityError("simulated identity race")
        original_save(card, *args, **kwargs)

    monkeypatch.setattr(Card, "save", raise_identity_race)

    with pytest.raises(CardIdentityConflict, match="Card identity conflicts"):
        change_card_identity(card=moving, label="Race Destination", card_pool="evil")

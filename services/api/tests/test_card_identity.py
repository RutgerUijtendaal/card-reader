from __future__ import annotations

import pytest

from card_reader_core.models import Card, CardAlias
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

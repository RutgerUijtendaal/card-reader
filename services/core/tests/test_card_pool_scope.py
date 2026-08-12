from __future__ import annotations

import pytest

from card_reader_core.models import (
    ALL_CARD_POOLS_SCOPE,
    EVIL_CARD_POOL,
    NEUTRAL_CARD_POOL,
    PLAYER_CARD_POOL,
    PLAYER_CARD_POOL_SCOPE,
    CardPoolScope,
)


def test_canonical_card_pool_scopes_expose_expected_visibility() -> None:
    assert PLAYER_CARD_POOL_SCOPE.allowed_pools == frozenset({PLAYER_CARD_POOL})
    assert PLAYER_CARD_POOL_SCOPE.allows_card_pool(PLAYER_CARD_POOL)
    assert not PLAYER_CARD_POOL_SCOPE.allows_card_pool(EVIL_CARD_POOL)
    assert not PLAYER_CARD_POOL_SCOPE.allows_card_pool(NEUTRAL_CARD_POOL)

    assert ALL_CARD_POOLS_SCOPE.allowed_pools == frozenset(
        {PLAYER_CARD_POOL, EVIL_CARD_POOL, NEUTRAL_CARD_POOL}
    )
    assert ALL_CARD_POOLS_SCOPE.allows_card_pool(PLAYER_CARD_POOL)
    assert ALL_CARD_POOLS_SCOPE.allows_card_pool(EVIL_CARD_POOL)
    assert ALL_CARD_POOLS_SCOPE.allows_card_pool(NEUTRAL_CARD_POOL)


def test_card_pool_scope_normalizes_and_rejects_unknown_pools() -> None:
    scope = CardPoolScope(frozenset({PLAYER_CARD_POOL}))

    assert scope.allowed_pools == frozenset({PLAYER_CARD_POOL})
    assert not scope.allows_card_pool("unknown")

    with pytest.raises(ValueError, match="Unsupported card pool scope values: secret"):
        CardPoolScope(frozenset({"secret"}))  # type: ignore[arg-type]

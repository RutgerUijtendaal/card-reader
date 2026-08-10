from __future__ import annotations

from types import SimpleNamespace

from card_reader_api.common.auth_access import card_pool_scope_for_user
from card_reader_core.models import ALL_CARD_POOLS_SCOPE, PLAYER_CARD_POOL_SCOPE


def test_card_pool_scope_for_user_maps_only_authenticated_staff_to_all_pools() -> None:
    anonymous = SimpleNamespace(is_authenticated=False, is_staff=True)
    regular_user = SimpleNamespace(is_authenticated=True, is_staff=False)
    staff_user = SimpleNamespace(is_authenticated=True, is_staff=True)

    assert card_pool_scope_for_user(anonymous) is PLAYER_CARD_POOL_SCOPE
    assert card_pool_scope_for_user(regular_user) is PLAYER_CARD_POOL_SCOPE
    assert card_pool_scope_for_user(staff_user) is ALL_CARD_POOLS_SCOPE

from __future__ import annotations

from types import SimpleNamespace

from card_reader_api.common.auth_access import capability_payload, card_pool_scope_for_user
from card_reader_core.models import ALL_CARD_POOLS_SCOPE, PLAYER_CARD_POOL_SCOPE


def test_card_pool_scope_for_user_maps_only_active_authenticated_staff_to_all_pools() -> None:
    anonymous = SimpleNamespace(is_authenticated=False, is_active=True, is_staff=True)
    inactive_staff = SimpleNamespace(is_authenticated=True, is_active=False, is_staff=True)
    regular_user = SimpleNamespace(is_authenticated=True, is_active=True, is_staff=False)
    staff_user = SimpleNamespace(is_authenticated=True, is_active=True, is_staff=True)

    assert card_pool_scope_for_user(anonymous) is PLAYER_CARD_POOL_SCOPE
    assert card_pool_scope_for_user(inactive_staff) is PLAYER_CARD_POOL_SCOPE
    assert card_pool_scope_for_user(regular_user) is PLAYER_CARD_POOL_SCOPE
    assert card_pool_scope_for_user(staff_user) is ALL_CARD_POOLS_SCOPE


def test_inactive_session_has_no_protected_capabilities() -> None:
    inactive_staff = SimpleNamespace(
        is_authenticated=True,
        is_active=False,
        is_staff=True,
        is_superuser=True,
    )

    assert capability_payload(inactive_staff) == {
        "can_access_authenticated_features": False,
        "can_access_admin": False,
        "accessible_card_pools": ["player"],
        "can_manage_users": False,
        "can_access_maintenance": False,
        "can_download_developer_data": False,
        "can_manage_developer_data": False,
    }

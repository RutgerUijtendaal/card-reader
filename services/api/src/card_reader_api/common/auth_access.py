from __future__ import annotations

from typing import Any

from card_reader_core.models import (
    ALL_CARD_POOLS_SCOPE,
    CARD_POOL_DEFINITIONS,
    PLAYER_CARD_POOL_SCOPE,
    CardPool,
    CardPoolScope,
)
from card_reader_core.services.user_roles import has_developer_role


def is_authenticated(user: Any) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def can_access_admin(user: Any) -> bool:
    return is_authenticated(user) and bool(getattr(user, "is_staff", False))


def card_pool_scope_for_user(user: Any) -> CardPoolScope:
    """Translate the current entitlement policy into a core data scope."""
    return ALL_CARD_POOLS_SCOPE if can_access_admin(user) else PLAYER_CARD_POOL_SCOPE


def accessible_card_pools_for_user(user: Any) -> list[CardPool]:
    scope = card_pool_scope_for_user(user)
    return [
        definition.key
        for definition in CARD_POOL_DEFINITIONS
        if scope.allows_card_pool(definition.key)
    ]


def can_access_authenticated_features(user: Any) -> bool:
    return is_authenticated(user)


def can_manage_users(user: Any) -> bool:
    return can_access_admin(user)


def can_access_maintenance(user: Any) -> bool:
    return is_authenticated(user) and bool(getattr(user, "is_superuser", False))


def can_download_developer_data(user: Any) -> bool:
    return (
        is_authenticated(user)
        and bool(getattr(user, "is_active", False))
        and (bool(getattr(user, "is_staff", False)) or has_developer_role(user))
    )


def can_manage_developer_data(user: Any) -> bool:
    return can_access_admin(user) and bool(getattr(user, "is_active", False))


def capability_payload(user: Any) -> dict[str, object]:
    return {
        "can_access_authenticated_features": can_access_authenticated_features(user),
        "can_access_admin": can_access_admin(user),
        "accessible_card_pools": accessible_card_pools_for_user(user),
        "can_manage_users": can_manage_users(user),
        "can_access_maintenance": can_access_maintenance(user),
        "can_download_developer_data": can_download_developer_data(user),
        "can_manage_developer_data": can_manage_developer_data(user),
    }

from __future__ import annotations

from typing import Any


def is_authenticated(user: Any) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def can_access_admin(user: Any) -> bool:
    return is_authenticated(user) and bool(getattr(user, "is_staff", False))


def can_access_authenticated_features(user: Any) -> bool:
    return is_authenticated(user)


def can_manage_users(user: Any) -> bool:
    return can_access_admin(user)


def can_access_maintenance(user: Any) -> bool:
    return is_authenticated(user) and bool(getattr(user, "is_superuser", False))


def capability_payload(user: Any) -> dict[str, bool]:
    return {
        "can_access_authenticated_features": can_access_authenticated_features(user),
        "can_access_admin": can_access_admin(user),
        "can_manage_users": can_manage_users(user),
        "can_access_maintenance": can_access_maintenance(user),
    }

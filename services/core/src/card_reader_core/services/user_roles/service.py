from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group

DEVELOPER_ROLE_NAME = "Developer"


def has_developer_role(user: Any) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    prefetched_groups = getattr(user, "_prefetched_objects_cache", {}).get("groups")
    if prefetched_groups is not None:
        return any(group.name == DEVELOPER_ROLE_NAME for group in prefetched_groups)
    return bool(user.groups.filter(name=DEVELOPER_ROLE_NAME).exists())


def set_developer_role(user: Any, *, enabled: bool) -> None:
    if enabled:
        group, _created = Group.objects.get_or_create(name=DEVELOPER_ROLE_NAME)
        user.groups.add(group)
        return
    user.groups.remove(*Group.objects.filter(name=DEVELOPER_ROLE_NAME))

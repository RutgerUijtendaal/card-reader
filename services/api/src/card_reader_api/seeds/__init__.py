from __future__ import annotations

from typing import Any

__all__ = ["seed_users", "seed_users_from_config"]


def __getattr__(name: str) -> Any:
    if name == "seed_users":
        from .users import seed_users

        return seed_users
    if name == "seed_users_from_config":
        from .users import seed_users_from_config

        return seed_users_from_config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


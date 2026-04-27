from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .runner import run_registered_seeds

__all__ = ["run_registered_seeds"]


def __getattr__(name: str) -> Any:
    if name == "run_registered_seeds":
        from .runner import run_registered_seeds as value

        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


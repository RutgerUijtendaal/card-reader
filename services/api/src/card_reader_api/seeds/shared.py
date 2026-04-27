from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(slots=True)
class SeedResult:
    name: str
    skipped: bool
    created: int = 0
    updated: int = 0
    message: str = ""


@dataclass(slots=True)
class SeedDefinition:
    name: str
    model_has_rows: Callable[[], bool]
    run: Callable[[], tuple[int, int]]


def resolve_seed_file(relative_from_seed_root: str) -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass) / "seeds" / relative_from_seed_root
    return Path(__file__).resolve().parent / relative_from_seed_root


def model_has_any_rows(model: type[Any]) -> bool:
    return bool(model.objects.exists())

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from sqlmodel import Session, select

logger = logging.getLogger(__name__)


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
    model_has_rows: Callable[[Session], bool]
    run: Callable[[Session], tuple[int, int]]


def resolve_seed_file(relative_from_seed_root: str) -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass) / "seeds" / relative_from_seed_root
    return Path(__file__).resolve().parent / relative_from_seed_root


def model_has_any_rows(session: Session, model: type[Any]) -> bool:
    return session.exec(select(getattr(model, "id")).limit(1)).first() is not None

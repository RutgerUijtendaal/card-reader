from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from card_reader_core.models import (
    DEFAULT_CARD_POOL,
    CardFaction,
    CardPool,
    CardRole,
    ImportJob,
    Template,
)

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class ImportJobInputValidationError(ValueError):
    """A definitive import-job input rejection raised before durable creation."""


@dataclass(frozen=True)
class ImportJobItemTarget:
    card_id: str
    card_version_id: str
    card_pool: CardPool = DEFAULT_CARD_POOL
    card_roles: tuple[CardRole, ...] = ()
    card_factions: tuple[CardFaction, ...] = ()


@dataclass(frozen=True)
class ImportJobCreationResult:
    job: ImportJob
    outcome: Literal["created", "replayed"]

    @property
    def idempotent_replay(self) -> bool:
        return self.outcome == "replayed"


@dataclass(frozen=True)
class PreparedImportJobInputs:
    template: Template
    card_role_mode: str
    card_role_override: tuple[CardRole, ...]
    template_roles: tuple[CardRole, ...]
    card_faction_mode: str
    card_faction_override: tuple[CardFaction, ...]
    template_factions: tuple[CardFaction, ...]
    inference_policy_version: int


class GroupedReparseSource(Protocol):
    @property
    def card_id(self) -> str: ...

    @property
    def card_version_id(self) -> str: ...

    @property
    def template_id(self) -> str: ...

    @property
    def image_path(self) -> Path: ...

    @property
    def card_pool(self) -> CardPool: ...

    @property
    def card_roles(self) -> tuple[CardRole, ...]: ...

    @property
    def card_factions(self) -> tuple[CardFaction, ...]: ...


@dataclass(frozen=True)
class GroupedReparseSummary:
    job_count: int
    item_count: int

from __future__ import annotations

from dataclasses import dataclass


class CardMergeError(ValueError):
    pass


@dataclass(frozen=True)
class CardMergeCardSummary:
    id: str
    key: str
    label: str
    latest_name: str
    version_count: int


@dataclass(frozen=True)
class CardMergeAliasPreview:
    key: str
    label: str
    conflict_card_id: str | None


@dataclass(frozen=True)
class CardMergeRelationPreview:
    deck_entry_collisions: int
    sideboard_entry_collisions: int
    group_member_collisions: int
    hero_references: int
    anchored_groups: int


@dataclass(frozen=True)
class CardMergePreview:
    target: CardMergeCardSummary
    sources: list[CardMergeCardSummary]
    aliases: list[CardMergeAliasPreview]
    relations: CardMergeRelationPreview
    resulting_version_count: int
    blocking_conflicts: list[str]

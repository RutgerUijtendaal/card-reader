from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEVELOPER_DATA_FORMAT_VERSION = 2
SUPPORTED_DEVELOPER_DATA_FORMAT_VERSIONS = (1, DEVELOPER_DATA_FORMAT_VERSION)


def _default_pool_coverage() -> dict[Literal["player", "game_master"], int]:
    return {"player": 1, "game_master": 0}


def _default_role_coverage() -> dict[Literal["standard", "hero", "boon", "event"], int]:
    return {"standard": 1, "hero": 1, "boon": 0, "event": 0}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CoverageRequirements(StrictModel):
    min_cards: int = Field(default=1, ge=0)
    min_cards_by_pool: dict[Literal["player", "game_master"], int] = Field(
        default_factory=_default_pool_coverage
    )
    min_cards_by_role: dict[Literal["standard", "hero", "boon", "event"], int] = Field(
        default_factory=_default_role_coverage
    )
    min_deprecated_cards: int = Field(default=1, ge=0)
    min_card_groups: int = Field(default=1, ge=0)
    min_cards_with_multiple_versions: int = Field(default=1, ge=0)
    required_template_keys: list[str] = Field(default_factory=list)


class DeveloperDataSelection(StrictModel):
    bundle_version: str = Field(min_length=1)
    include_all_cards: bool = False
    include_all_card_groups: bool = False
    card_keys: list[str] = Field(default_factory=list)
    card_group_keys: list[str] = Field(default_factory=list)
    coverage: CoverageRequirements = Field(default_factory=CoverageRequirements)


class CatalogRecord(StrictModel):
    key: str
    label: str
    identifiers: list[str]


class SymbolRecord(StrictModel):
    key: str
    label: str
    symbol_type: str
    detector_type: str
    detection_config: dict[str, Any]
    text_enrichment: dict[str, Any]
    reference_assets: list[str]
    text_token: str
    enabled: bool


class TemplateRecord(StrictModel):
    key: str
    label: str
    definition: dict[str, Any]


class DeckTagRecord(StrictModel):
    kind: str
    key: str
    label: str


class ContentVersionRecord(StrictModel):
    version_number: str
    base_version: str
    major: int
    minor: int
    patch: int
    description: str


class CardImageRecord(StrictModel):
    stored_path: str
    width: int
    height: int
    checksum: str


class CardVersionRecord(StrictModel):
    version_number: int
    template_key: str
    image_hash: str
    name: str
    type_line: str
    mana_cost: str
    mana_symbols: list[Any]
    mana_value: int | None
    attack: int | None
    health: int | None
    rules_text_raw: str
    rules_text_enriched: str
    rules_text: str
    confidence: float
    field_sources: dict[str, Any]
    parsed_snapshot: dict[str, Any]
    is_latest: bool
    previous_version_number: int | None
    content_version_number: str | None
    keyword_keys: list[str]
    tag_keys: list[str]
    symbol_keys: list[str]
    type_keys: list[str]
    images: list[CardImageRecord]


class CardAliasRecord(StrictModel):
    key: str
    label: str


class CardRecord(StrictModel):
    key: str
    label: str
    card_pool: Literal["player", "game_master"]
    card_roles: list[Literal["hero", "boon", "event"]]
    deck_building_config: dict[str, Any]
    lifecycle_status: str
    latest_version_number: int | None
    aliases: list[CardAliasRecord]
    versions: list[CardVersionRecord]

    @field_validator("card_roles")
    @classmethod
    def validate_unique_card_roles(
        cls,
        value: list[Literal["hero", "boon", "event"]],
    ) -> list[Literal["hero", "boon", "event"]]:
        if len(value) != len(set(value)):
            raise ValueError("Card roles must be unique.")
        return value


class CardGroupMemberRecord(StrictModel):
    card_key: str
    position: int


class CardGroupRecord(StrictModel):
    key: str
    name: str
    anchor_card_key: str
    members: list[CardGroupMemberRecord]


class CardBackRecord(StrictModel):
    label: str
    stored_path: str
    width: int
    height: int
    checksum: str


class DeveloperDataPayload(StrictModel):
    keywords: list[CatalogRecord]
    tags: list[CatalogRecord]
    types: list[CatalogRecord]
    symbols: list[SymbolRecord]
    templates: list[TemplateRecord]
    deck_tags: list[DeckTagRecord]
    content_versions: list[ContentVersionRecord]
    cards: list[CardRecord]
    card_groups: list[CardGroupRecord]
    current_card_back: CardBackRecord | None


class BundleFileRecord(StrictModel):
    path: str
    sha256: str
    size_bytes: int


class DeveloperDataManifest(StrictModel):
    format_version: int
    bundle_version: str
    created_at: datetime
    source_revision: str
    source_migration: str
    selection_sha256: str
    counts: dict[str, int]
    files: list[BundleFileRecord]


class PublishedBundle(StrictModel):
    bundle_version: str
    format_version: int
    filename: str
    sha256: str
    size_bytes: int
    created_at: datetime


class DeveloperDataLock(StrictModel):
    bundle_version: str
    format_version: int
    sha256: str
    api_base_url: str


def adopt_payload_for_format(value: object, *, format_version: int) -> object:
    """Adopt older bundle payloads into the current strict schema."""
    if format_version != 1 or not isinstance(value, dict):
        return value
    adopted = dict(value)
    cards = adopted.get("cards")
    if not isinstance(cards, list):
        return adopted
    adopted_cards: list[object] = []
    for card in cards:
        if not isinstance(card, dict):
            adopted_cards.append(card)
            continue
        adopted_card = dict(card)
        if "is_hero" not in adopted_card or type(adopted_card["is_hero"]) is not bool:
            raise ValueError("Legacy developer-data card is_hero must be a Boolean.")
        was_hero = adopted_card.pop("is_hero")
        adopted_card["card_pool"] = "player"
        adopted_card["card_roles"] = ["hero"] if was_hero is True else []
        adopted_cards.append(adopted_card)
    adopted["cards"] = adopted_cards
    return adopted

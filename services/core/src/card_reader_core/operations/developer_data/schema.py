from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from card_reader_core.models import (
    CARD_ROLE_FILTER_VALUES,
    CARD_FACTIONS,
    HERO_CARD_ROLE,
    STANDARD_CARD_ROLE,
    CardFaction,
    CardPool,
    CardRole,
    CardRoleFilter,
    normalize_card_factions,
    normalize_card_roles,
)
from card_reader_core.metadata import (
    ManaFamily,
    mana_family_keys_for_symbol_keys,
    normalize_mana_family_keys,
)

DEVELOPER_DATA_FORMAT_VERSION = 3
SUPPORTED_DEVELOPER_DATA_FORMAT_VERSIONS = (1, 2, DEVELOPER_DATA_FORMAT_VERSION)
LEGACY_ROLE_TYPE_POOLS: tuple[tuple[CardRole, frozenset[CardPool]], ...] = (
    ("directive", frozenset({"evil"})),
    ("reminder", frozenset({"evil"})),
    ("mana", frozenset({"player", "evil"})),
)


def _default_pool_coverage() -> dict[CardPool, int]:
    return {"player": 1, "evil": 0, "neutral": 0}


def _default_role_coverage() -> dict[CardRoleFilter, int]:
    coverage: dict[CardRoleFilter, int] = {role: 0 for role in CARD_ROLE_FILTER_VALUES}
    coverage[STANDARD_CARD_ROLE] = 1
    coverage[HERO_CARD_ROLE] = 1
    return coverage


def _default_faction_coverage() -> dict[CardFaction, int]:
    return {faction: 0 for faction in CARD_FACTIONS}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClassificationRuleRecord(StrictModel):
    card_pool: CardPool
    target_kind: str
    target_key: str
    source_kind: str
    source_key: str
    enabled: bool = True

    @field_validator("target_kind")
    @classmethod
    def validate_target_kind(cls, value: str) -> str:
        if value not in {"role", "faction", "mana_family"}:
            raise ValueError(
                "Classification rule target_kind must be role, faction, or mana_family."
            )
        return value

    @field_validator("source_kind")
    @classmethod
    def validate_source_kind(cls, value: str) -> str:
        if value not in {"tag", "type", "symbol"}:
            raise ValueError("Classification rule source_kind must be tag, type, or symbol.")
        return value


class CoverageRequirements(StrictModel):
    min_cards: int = Field(default=1, ge=0)
    min_cards_by_pool: dict[CardPool, int] = Field(default_factory=_default_pool_coverage)
    min_cards_by_role: dict[CardRoleFilter, int] = Field(default_factory=_default_role_coverage)
    min_cards_by_faction: dict[CardFaction, int] = Field(default_factory=_default_faction_coverage)
    min_cards_by_mana_family: dict[ManaFamily, int] = Field(default_factory=dict)
    min_deprecated_cards: int = Field(default=1, ge=0)
    min_card_groups: int = Field(default=1, ge=0)
    min_cards_with_multiple_versions: int = Field(default=1, ge=0)
    required_template_keys: list[str] = Field(default_factory=list)
    required_tag_keys: list[str] = Field(default_factory=list)
    required_classification_rules: list[ClassificationRuleRecord] = Field(default_factory=list)


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


class CardReferenceRecord(StrictModel):
    key: str
    card_pool: CardPool
    card_factions: list[CardFaction]
    card_mana_families: list[ManaFamily]

    @field_validator("card_factions")
    @classmethod
    def validate_unique_card_factions(
        cls,
        value: list[CardFaction],
    ) -> list[CardFaction]:
        if len(value) != len(set(value)):
            raise ValueError("Card reference factions must be unique.")
        return list(normalize_card_factions(value))

    @field_validator("card_mana_families")
    @classmethod
    def validate_unique_card_mana_families(
        cls,
        value: list[ManaFamily],
    ) -> list[ManaFamily]:
        if len(value) != len(set(value)):
            raise ValueError("Card mana families must be unique.")
        return list(normalize_mana_family_keys(tuple(value)))


type CardReferenceIdentity = tuple[CardPool, tuple[CardFaction, ...], str]


def card_reference_identity(
    reference: CardReferenceRecord,
) -> CardReferenceIdentity:
    return (
        reference.card_pool,
        normalize_card_factions(reference.card_factions),
        reference.key,
    )


class CardRecord(StrictModel):
    key: str
    label: str
    card_pool: CardPool
    card_roles: list[CardRole]
    card_factions: list[CardFaction]
    card_mana_families: list[ManaFamily]
    deck_building_config: dict[str, Any]
    lifecycle_status: str
    latest_version_number: int | None
    aliases: list[CardAliasRecord]
    versions: list[CardVersionRecord]

    @field_validator("card_roles")
    @classmethod
    def validate_unique_card_roles(
        cls,
        value: list[CardRole],
    ) -> list[CardRole]:
        if len(value) != len(set(value)):
            raise ValueError("Card roles must be unique.")
        return value

    @field_validator("card_factions")
    @classmethod
    def validate_unique_card_factions(
        cls,
        value: list[CardFaction],
    ) -> list[CardFaction]:
        if len(value) != len(set(value)):
            raise ValueError("Card factions must be unique.")
        return list(normalize_card_factions(value))

    @field_validator("card_mana_families")
    @classmethod
    def validate_unique_card_mana_families(
        cls,
        value: list[ManaFamily],
    ) -> list[ManaFamily]:
        if len(value) != len(set(value)):
            raise ValueError("Card mana families must be unique.")
        return list(normalize_mana_family_keys(tuple(value)))


class CardGroupMemberRecord(StrictModel):
    card_ref: CardReferenceRecord
    position: int


class CardGroupRecord(StrictModel):
    key: str
    name: str
    anchor_card_ref: CardReferenceRecord
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
    classification_rules: list[ClassificationRuleRecord]
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
    if format_version not in {1, 2} or not isinstance(value, dict):
        return value
    adopted = dict(value)
    if format_version == 1:
        adopted["classification_rules"] = []
    cards = adopted.get("cards")
    if not isinstance(cards, list):
        return adopted
    adopted_cards: list[object] = []
    for card in cards:
        if not isinstance(card, dict):
            adopted_cards.append(card)
            continue
        adopted_card = dict(card)
        if format_version == 1:
            if "is_hero" not in adopted_card or type(adopted_card["is_hero"]) is not bool:
                raise ValueError("Legacy developer-data card is_hero must be a Boolean.")
            was_hero = adopted_card.pop("is_hero")
            adopted_card["card_pool"] = "player"
            adopted_card["card_roles"] = ["hero"] if was_hero is True else []
            adopted_card["card_factions"] = []
        latest_number = adopted_card.get("latest_version_number")
        versions = adopted_card.get("versions", [])
        latest_version = next(
            (
                version
                for version in versions
                if isinstance(version, dict)
                and version.get("version_number") == latest_number
            ),
            None,
        )
        role_values = adopted_card.get("card_roles", [])
        type_keys = (
            latest_version.get("type_keys", [])
            if isinstance(latest_version, dict)
            else []
        )
        if isinstance(role_values, list) and isinstance(type_keys, list):
            normalized_type_keys = {
                key.strip().casefold() for key in type_keys if isinstance(key, str)
            }
            card_pool = adopted_card.get("card_pool")
            inferred_roles = tuple(
                role
                for role, pools in LEGACY_ROLE_TYPE_POOLS
                if card_pool in pools and role in normalized_type_keys
            )
            if inferred_roles:
                adopted_card["card_roles"] = list(
                    normalize_card_roles((*role_values, *inferred_roles))
                )
        symbol_keys = (
            latest_version.get("symbol_keys", [])
            if isinstance(latest_version, dict)
            else []
        )
        adopted_card["card_mana_families"] = (
            list(
                mana_family_keys_for_symbol_keys(
                    tuple(str(key) for key in symbol_keys if isinstance(key, str))
                )
            )
            if adopted_card.get("card_pool") == "player"
            else []
        )
        adopted_cards.append(adopted_card)
    adopted["cards"] = adopted_cards
    if format_version != 1:
        families_by_reference = {
            (
                card.get("key"),
                card.get("card_pool"),
                tuple(normalize_card_factions(card.get("card_factions", []))),
            ): list(card.get("card_mana_families", []))
            for card in adopted_cards
            if isinstance(card, dict)
            and isinstance(card.get("card_factions", []), list)
        }

        def adopt_reference(reference: object) -> object:
            if not isinstance(reference, dict):
                return reference
            identity = (
                reference.get("key"),
                reference.get("card_pool"),
                tuple(normalize_card_factions(reference.get("card_factions", []))),
            )
            return {
                **reference,
                "card_mana_families": families_by_reference.get(identity, []),
            }

        groups = adopted.get("card_groups")
        if isinstance(groups, list):
            adopted["card_groups"] = [
                {
                    **group,
                    "anchor_card_ref": adopt_reference(group.get("anchor_card_ref")),
                    "members": [
                        {
                            **member,
                            "card_ref": adopt_reference(member.get("card_ref")),
                        }
                        if isinstance(member, dict)
                        else member
                        for member in group.get("members", [])
                    ],
                }
                if isinstance(group, dict)
                else group
                for group in groups
            ]
        return adopted
    cards_by_key = {
        card["key"]: {
            "key": card["key"],
            "card_pool": card["card_pool"],
            "card_factions": card["card_factions"],
            "card_mana_families": card["card_mana_families"],
        }
        for card in adopted_cards
        if isinstance(card, dict)
    }
    if len(cards_by_key) != len(adopted_cards):
        raise ValueError("Legacy developer-data card keys must be unique.")
    groups = adopted.get("card_groups")
    if isinstance(groups, list):
        adopted["card_groups"] = [
            {
                **{
                    key: item
                    for key, item in group.items()
                    if key not in {"anchor_card_key", "members"}
                },
                "anchor_card_ref": cards_by_key.get(group.get("anchor_card_key")),
                "members": [
                    {
                        **{key: item for key, item in member.items() if key != "card_key"},
                        "card_ref": cards_by_key.get(member.get("card_key")),
                    }
                    if isinstance(member, dict)
                    else member
                    for member in group.get("members", [])
                ],
            }
            if isinstance(group, dict)
            else group
            for group in groups
        ]
    return adopted

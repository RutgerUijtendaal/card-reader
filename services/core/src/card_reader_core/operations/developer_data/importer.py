from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import shutil
from typing import Any
from uuid import UUID, uuid5

from django.db import transaction

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    CARD_FACTIONS,
    CARD_ROLES,
    Card,
    CardAlias,
    CardBack,
    CardClassificationRule,
    CardGroup,
    CardGroupMember,
    CardFactionAssignment,
    CardRoleAssignment,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    ContentVersion,
    DeckTag,
    Keyword,
    Symbol,
    Tag,
    Template,
    TtsCardSheet,
    Type,
    card_faction_identity_key,
)
from card_reader_core.repositories.cards import lock_card_identity_pools, set_card_mana_families
from card_reader_core.rules import render_enriched_rule_text
from card_reader_core.services.classification_rules import (
    ClassificationRuleService,
    ensure_default_mana_family_classification_rules,
)
from card_reader_core.services.templates import apply_bundled_template_compatibility
from card_reader_core.services.card_backs import (
    select_card_back_override,
    set_faction_default,
    set_pool_default,
    set_role_default,
)
from card_reader_core.metadata import MANA_FAMILY_BY_KEY
from card_reader_core.storage import calculate_checksum

from .archive import DeveloperDataError, extracted_archive, load_extracted_bundle
from .schema import (
    CardReferenceRecord,
    CardReferenceIdentity,
    CardRecord as DeveloperDataCardRecord,
    DeveloperDataManifest,
    DeveloperDataPayload,
    card_reference_identity,
)


MIGRATION_DEFAULT_NAMESPACE = UUID("d5050158-0d5c-419c-9506-e704938447c9")
MIGRATION_DEFAULT_SOURCE_DEFINITIONS = {
    "tag": {
        "order": ("Order", ["order"]),
        "blood": ("Blood", ["blood"]),
        "dark": ("Dark", ["dark"]),
        "metal": ("Metal", ["metal"]),
        "fire": ("Fire", ["fire"]),
    },
    "type": {
        "hero": ("Hero", ["hero"]),
        "boss": ("Boss", ["boss"]),
        "boon": ("Boon", ["boon"]),
        "event": ("Event", ["event"]),
        "location": ("Location", ["location"]),
        "directive": ("Directive", ["directive"]),
        "reminder": ("Reminder", ["reminder"]),
        "mana": ("Mana", ["mana"]),
    },
}
MIGRATION_DEFAULT_CLASSIFICATION_RULES = (
    ("player", "role", "hero", "type", "hero"),
    ("player", "role", "mana", "type", "mana"),
    ("evil", "role", "boss", "type", "boss"),
    ("evil", "role", "location", "type", "location"),
    ("evil", "role", "directive", "type", "directive"),
    ("evil", "role", "reminder", "type", "reminder"),
    ("evil", "role", "mana", "type", "mana"),
    ("evil", "faction", "order", "tag", "order"),
    ("evil", "faction", "blood", "tag", "blood"),
    ("evil", "faction", "dark", "tag", "dark"),
    ("evil", "faction", "metal", "tag", "metal"),
    ("evil", "faction", "fire", "tag", "fire"),
    ("neutral", "role", "boon", "type", "boon"),
    ("neutral", "role", "event", "type", "event"),
)
MIGRATION_DEFAULT_FULL_HEIGHT_TEMPLATE: dict[str, Any] = {
    "id": "full-height",
    "version": 1,
    "regions": [
        {
            "region_id": "top_bar",
            "parser_type": "name",
            "cut_region": {
                "unit": "relative",
                "x": 0.04,
                "y": 0.02,
                "w": 0.92,
                "h": 0.07,
            },
            "ocr_config": {"ocr_min_confidence": 0.55},
        },
        {
            "region_id": "type_bar",
            "parser_type": "type_tag",
            "cut_region": {
                "unit": "relative",
                "x": 0.05,
                "y": 0.93,
                "w": 0.9,
                "h": 0.06,
            },
            "ocr_config": {},
        },
        {
            "region_id": "rules_text",
            "parser_type": "rules_text",
            "cut_region": {
                "unit": "relative",
                "x": 0.05,
                "y": 0.09,
                "w": 0.9,
                "h": 0.84,
            },
            "ocr_config": {},
        },
        {
            "region_id": "rules_text_fallback",
            "parser_type": "rules_text",
            "cut_region": {
                "unit": "relative",
                "x": 0.05,
                "y": 0.37,
                "w": 0.9,
                "h": 0.3,
            },
            "ocr_config": {},
        },
    ],
}


def _migration_default_id(kind: str, identity: str) -> str:
    return str(uuid5(MIGRATION_DEFAULT_NAMESPACE, f"{kind}:{identity}"))


def _migration_default_rule_id(rule: tuple[str, str, str, str, str]) -> str:
    return _migration_default_id("classification-rule", ":".join(rule))


@dataclass(frozen=True)
class DeveloperDataImportResult:
    bundle_version: str
    counts: dict[str, int]
    copied_assets: int


def import_developer_data(
    *,
    archive_path: Path,
    expected_bundle_version: str | None = None,
    expected_archive_sha256: str | None = None,
) -> DeveloperDataImportResult:
    if expected_archive_sha256 is not None:
        actual_archive_sha256 = calculate_checksum(archive_path)
        if actual_archive_sha256 != expected_archive_sha256:
            raise DeveloperDataError(
                "Developer-data archive checksum does not match the lock file."
            )
    with extracted_archive(archive_path) as extraction_root:
        manifest, payload = load_extracted_bundle(extraction_root)
        if (
            expected_bundle_version is not None
            and manifest.bundle_version != expected_bundle_version
        ):
            raise DeveloperDataError(
                f"Expected developer-data bundle {expected_bundle_version}, found {manifest.bundle_version}."
            )
        _validate_payload_references(payload)
        asset_paths = _validate_payload_assets(payload=payload, manifest=manifest)
        _ensure_domain_is_empty(payload)
        with _copied_assets(
            extraction_root=extraction_root,
            manifest=manifest,
            asset_paths=asset_paths,
        ) as created_assets:
            with transaction.atomic():
                lock_card_identity_pools("player")
                _import_payload(
                    payload,
                    source_format_version=manifest.format_version,
                )
    return DeveloperDataImportResult(
        bundle_version=manifest.bundle_version,
        counts=manifest.counts,
        copied_assets=len(created_assets),
    )


def validate_import_readiness(payload: DeveloperDataPayload) -> list[str]:
    issues: list[str] = []
    _append_empty_selection_issues(payload, issues)
    _append_player_card_readiness_issues(payload, issues)
    _append_player_card_back_readiness_issue(payload, issues)
    return issues


def _append_empty_selection_issues(
    payload: DeveloperDataPayload,
    issues: list[str],
) -> None:
    required_collections = (
        (payload.keywords, "keyword catalog"),
        (payload.tags, "tag catalog"),
        (payload.types, "type catalog"),
        (payload.symbols, "symbol catalog"),
        (payload.templates, "template catalog"),
        (payload.deck_tags, "deck-tag catalog"),
        (payload.cards, "card selection"),
    )
    for collection, label in required_collections:
        if not collection:
            issues.append(f"{label} is empty")


def _append_player_card_readiness_issues(
    payload: DeveloperDataPayload,
    issues: list[str],
) -> None:
    has_active_hero = any(
        card.card_pool == "player"
        and "hero" in card.card_roles
        and card.lifecycle_status == "active"
        for card in payload.cards
    )
    if not has_active_hero:
        issues.append("no active hero is included")

    has_active_mainboard_card = any(
        "hero" not in card.card_roles
        and card.card_pool == "player"
        and card.lifecycle_status == "active"
        for card in payload.cards
    )
    if not has_active_mainboard_card:
        issues.append("no active mainboard cards are included")


def _append_player_card_back_readiness_issue(
    payload: DeveloperDataPayload,
    issues: list[str],
) -> None:
    player_default = next(
        (
            row.card_back_checksum
            for row in payload.card_back_pool_defaults
            if row.card_pool == "player"
        ),
        None,
    )
    if player_default is None:
        issues.append("Player pool default card back is missing")


def _ensure_domain_is_empty(payload: DeveloperDataPayload) -> None:
    populated: list[str] = []
    for model in (
        Card,
        CardBack,
        CardClassificationRule,
        CardGroup,
        ContentVersion,
        Keyword,
        Symbol,
        Tag,
        Template,
        TtsCardSheet,
        Type,
    ):
        if _model_contains_non_migration_defaults(model):
            populated.append(str(model._meta.verbose_name_plural))
    expected_deck_tags = {(row.kind, row.key): row.label for row in payload.deck_tags}
    incompatible_deck_tags = [
        deck_tag
        for deck_tag in DeckTag.objects.all()
        if expected_deck_tags.get((deck_tag.kind, deck_tag.key)) != deck_tag.label
    ]
    if incompatible_deck_tags:
        populated.append("custom deck tags")
    if populated:
        raise DeveloperDataError(
            "Developer-data bootstrap requires an empty domain database; found data in: "
            + ", ".join(populated)
        )


def _model_contains_non_migration_defaults(model: Any) -> bool:
    if model not in {CardClassificationRule, Tag, Template, Type}:
        return bool(model.objects.exists())
    return any(not _is_unmodified_migration_default(model, row) for row in model.objects.all())


def _is_unmodified_migration_default(model: Any, row: Any) -> bool:
    if model is Tag:
        return _is_unmodified_migration_catalog_source(row, source_kind="tag")
    if model is Type:
        return _is_unmodified_migration_catalog_source(row, source_kind="type")
    if model is Template:
        return bool(
            row.id == _migration_default_id("template", "full-height")
            and row.key == "full-height"
            and row.label == "Full height"
            and row.definition_json == MIGRATION_DEFAULT_FULL_HEIGHT_TEMPLATE
        )
    return _is_unmodified_migration_rule(row)


def _is_unmodified_migration_catalog_source(row: Any, *, source_kind: str) -> bool:
    definition = MIGRATION_DEFAULT_SOURCE_DEFINITIONS[source_kind].get(row.key)
    if definition is None:
        return False
    label, identifiers = definition
    return bool(
        row.id == _migration_default_id(source_kind, row.key)
        and row.label == label
        and row.identifiers_json == identifiers
    )


def _is_unmodified_migration_rule(rule: Any) -> bool:
    definitions_by_id = {
        _migration_default_rule_id(definition): definition
        for definition in MIGRATION_DEFAULT_CLASSIFICATION_RULES
    }
    definition = definitions_by_id.get(rule.id)
    if definition is None:
        return False
    card_pool, target_kind, target_key, source_kind, source_key = definition
    expected_source_id = _migration_default_id(source_kind, source_key)
    return bool(
        rule.card_pool == card_pool
        and rule.target_kind == target_kind
        and rule.target_key == target_key
        and rule.source_kind == source_kind
        and rule.tag_id == (expected_source_id if source_kind == "tag" else None)
        and rule.type_id == (expected_source_id if source_kind == "type" else None)
        and rule.enabled is True
    )


@contextmanager
def _copied_assets(
    *,
    extraction_root: Path,
    manifest: DeveloperDataManifest,
    asset_paths: set[str],
) -> Iterator[list[Path]]:
    created: list[Path] = []
    try:
        _copy_assets(
            extraction_root=extraction_root,
            manifest=manifest,
            asset_paths=asset_paths,
            created=created,
        )
        yield created
    except BaseException:
        for asset_path in reversed(created):
            asset_path.unlink(missing_ok=True)
        raise


def _copy_assets(
    *,
    extraction_root: Path,
    manifest: DeveloperDataManifest,
    asset_paths: set[str],
    created: list[Path],
) -> None:
    storage_root = settings.storage_root_dir.resolve()
    entries = {entry.path: entry for entry in manifest.files}
    for relative_storage_path in sorted(asset_paths):
        entry_path = f"assets/{relative_storage_path}"
        entry = entries[entry_path]
        source = extraction_root / Path(entry_path)
        target = (storage_root / Path(relative_storage_path)).resolve()
        try:
            target.relative_to(storage_root)
        except ValueError as exc:
            raise DeveloperDataError(
                f"Asset target escapes storage root: {relative_storage_path}"
            ) from exc
        if target.exists():
            if (
                not target.is_file()
                or target.stat().st_size != entry.size_bytes
                or calculate_checksum(target) != entry.sha256
            ):
                raise DeveloperDataError(
                    f"Conflicting local asset already exists: {relative_storage_path}"
                )
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        created.append(target)


def _import_payload(
    payload: DeveloperDataPayload,
    *,
    source_format_version: int,
) -> None:
    card_backs = _import_card_backs(payload)
    catalogs = _import_catalogs(payload)
    _import_classification_rules(
        payload,
        catalogs=catalogs,
        source_format_version=source_format_version,
    )
    _import_deck_tags(payload)
    content_versions = _import_content_versions(payload)
    cards = _create_cards(payload, card_backs)
    for card_record in payload.cards:
        card = cards[_payload_card_identity(card_record)]
        _import_card_details(
            card_record,
            card=card,
            catalogs=catalogs,
            content_versions=content_versions,
        )
    _import_card_groups(payload, cards)


def _import_card_backs(payload: DeveloperDataPayload) -> dict[str, CardBack]:
    card_backs_by_checksum: dict[str, CardBack] = {}
    for card_back_record in payload.card_backs:
        card_back = CardBack.objects.create(
            label=card_back_record.label,
            original_filename=Path(card_back_record.stored_path).name,
            source_file=card_back_record.stored_path,
            stored_path=card_back_record.stored_path,
            width=card_back_record.width,
            height=card_back_record.height,
            checksum=card_back_record.checksum,
        )
        card_backs_by_checksum[card_back.checksum] = card_back
    for pool_default_record in payload.card_back_pool_defaults:
        if pool_default_record.card_back_checksum is not None:
            set_pool_default(
                pool_default_record.card_pool,
                card_backs_by_checksum[pool_default_record.card_back_checksum].id,
            )
    for faction_default_record in payload.card_back_faction_defaults:
        if faction_default_record.card_back_checksum is not None:
            set_faction_default(
                faction_default_record.faction,
                card_backs_by_checksum[faction_default_record.card_back_checksum].id,
            )
    for role_default_record in payload.card_back_role_defaults:
        if role_default_record.card_back_checksum is not None:
            set_role_default(
                role_default_record.role,
                card_backs_by_checksum[role_default_record.card_back_checksum].id,
            )
    return card_backs_by_checksum


@dataclass(frozen=True)
class _ImportedCatalogs:
    keywords: dict[str, Any]
    tags: dict[str, Any]
    types: dict[str, Any]
    symbols: dict[str, Symbol]
    templates: dict[str, Template]


def _import_catalogs(payload: DeveloperDataPayload) -> _ImportedCatalogs:
    keywords = _create_catalog_rows(Keyword, payload.keywords)
    tags = _create_catalog_rows(Tag, payload.tags)
    types = _create_catalog_rows(Type, payload.types)

    symbols: dict[str, Symbol] = {}
    for row in payload.symbols:
        reference_assets = []
        for asset_path in row.reference_assets:
            reference_assets.append(_symbol_reference_asset_path(asset_path))
        symbols[row.key] = Symbol.objects.create(
            key=row.key,
            label=row.label,
            symbol_type=row.symbol_type,
            detector_type=row.detector_type,
            detection_config_json=row.detection_config,
            text_enrichment_json=row.text_enrichment,
            reference_assets_json=reference_assets,
            text_token=row.text_token,
            enabled=row.enabled,
        )

    templates = _import_templates(payload)
    return _ImportedCatalogs(
        keywords=keywords,
        tags=tags,
        types=types,
        symbols=symbols,
        templates=templates,
    )


def _import_templates(payload: DeveloperDataPayload) -> dict[str, Template]:
    templates: dict[str, Template] = {}
    for template_record in payload.templates:
        template_definition = apply_bundled_template_compatibility(
            key=template_record.key,
            definition=template_record.definition,
        )
        template, _created = Template.objects.update_or_create(
            key=template_record.key,
            defaults={
                "label": template_record.label,
                "definition_json": template_definition,
            },
        )
        templates[template_record.key] = template
    return templates


def _import_classification_rules(
    payload: DeveloperDataPayload,
    *,
    catalogs: _ImportedCatalogs,
    source_format_version: int,
) -> None:
    sources_by_kind = {
        "tag": catalogs.tags,
        "type": catalogs.types,
        "symbol": catalogs.symbols,
    }
    service = ClassificationRuleService()
    for rule_record in payload.classification_rules:
        source = sources_by_kind[rule_record.source_kind][rule_record.source_key]
        source_fields = {
            "tag_id": source.id if rule_record.source_kind == "tag" else None,
            "type_id": source.id if rule_record.source_kind == "type" else None,
            "symbol_id": source.id if rule_record.source_kind == "symbol" else None,
        }
        existing_rule = CardClassificationRule.objects.filter(
            card_pool=rule_record.card_pool,
            target_kind=rule_record.target_kind,
            target_key=rule_record.target_key,
            source_kind=rule_record.source_kind,
            **source_fields,
        ).first()
        if existing_rule is None:
            service.create_rule(
                card_pool=rule_record.card_pool,
                target_kind=rule_record.target_kind,
                target_key=rule_record.target_key,
                source_kind=rule_record.source_kind,
                source_id=source.id,
                enabled=rule_record.enabled,
            )
            continue
        if existing_rule.enabled != rule_record.enabled:
            service.update_rule(
                rule_id=existing_rule.id,
                enabled=rule_record.enabled,
            )

    if source_format_version in {1, 2}:
        ensure_default_mana_family_classification_rules()


def _import_deck_tags(payload: DeveloperDataPayload) -> None:
    for deck_tag_record in payload.deck_tags:
        DeckTag.objects.update_or_create(
            kind=deck_tag_record.kind,
            key=deck_tag_record.key,
            defaults={"label": deck_tag_record.label},
        )


def _import_content_versions(payload: DeveloperDataPayload) -> dict[str, ContentVersion]:
    content_versions: dict[str, ContentVersion] = {}
    for row in payload.content_versions:
        content_versions[row.version_number] = ContentVersion.objects.create(
            version_number=row.version_number,
            base_version=row.base_version,
            major=row.major,
            minor=row.minor,
            patch=row.patch,
            description=row.description,
        )
    return content_versions


def _create_cards(
    payload: DeveloperDataPayload,
    card_backs: dict[str, CardBack],
) -> dict[CardReferenceIdentity, Card]:
    cards: dict[CardReferenceIdentity, Card] = {}
    for row in payload.cards:
        card_back_id = None
        if row.card_back_override_checksum is not None:
            card_back_id = card_backs[row.card_back_override_checksum].id
        cards[_payload_card_identity(row)] = Card.objects.create(
            key=row.key,
            label=row.label,
            card_pool=row.card_pool,
            faction_identity_key=card_faction_identity_key(row.card_factions),
            deck_building_config_json=row.deck_building_config,
            lifecycle_status=row.lifecycle_status,
            card_back_override=select_card_back_override(card_back_id),
        )
    return cards


def _import_card_details(
    card_record: DeveloperDataCardRecord,
    *,
    card: Card,
    catalogs: _ImportedCatalogs,
    content_versions: dict[str, ContentVersion],
) -> None:
    _import_card_classification(card_record, card)
    _import_card_aliases(card_record, card)
    version_models = _create_card_versions(
        card_record,
        card=card,
        catalogs=catalogs,
        content_versions=content_versions,
    )
    _import_card_version_relations(
        card_record,
        version_models=version_models,
        catalogs=catalogs,
    )
    if card_record.latest_version_number is not None:
        card.latest_version = version_models[card_record.latest_version_number]
        card.save(update_fields=["latest_version"])


def _import_card_classification(
    card_record: DeveloperDataCardRecord,
    card: Card,
) -> None:
    role_assignments = []
    for role in card_record.card_roles:
        role_assignments.append(CardRoleAssignment(card=card, role=role))
    CardRoleAssignment.objects.bulk_create(role_assignments)

    faction_assignments = []
    for faction in card_record.card_factions:
        faction_assignments.append(CardFactionAssignment(card=card, faction=faction))
    CardFactionAssignment.objects.bulk_create(faction_assignments)
    set_card_mana_families(card=card, mana_families=card_record.card_mana_families)


def _import_card_aliases(card_record: DeveloperDataCardRecord, card: Card) -> None:
    aliases = []
    for alias in card_record.aliases:
        aliases.append(
            CardAlias(
                card=card,
                card_pool=card.card_pool,
                faction_identity_key=card.faction_identity_key,
                key=alias.key,
                label=alias.label,
            )
        )
    CardAlias.objects.bulk_create(aliases)


def _create_card_versions(
    card_record: DeveloperDataCardRecord,
    *,
    card: Card,
    catalogs: _ImportedCatalogs,
    content_versions: dict[str, ContentVersion],
) -> dict[int, CardVersion]:
    version_models: dict[int, CardVersion] = {}
    for version in card_record.versions:
        symbol_tokens_by_key = {}
        for key in version.symbol_keys:
            symbol_tokens_by_key[key] = catalogs.symbols[key].text_token
        content_version = None
        if version.content_version_number is not None:
            content_version = content_versions[version.content_version_number]
        version_models[version.version_number] = CardVersion.objects.create(
            card=card,
            version_number=version.version_number,
            template=catalogs.templates[version.template_key],
            image_hash=version.image_hash,
            name=version.name,
            type_line=version.type_line,
            mana_cost=version.mana_cost,
            mana_symbols_json=version.mana_symbols,
            mana_value=version.mana_value,
            attack=version.attack,
            health=version.health,
            rules_text_raw=version.rules_text_raw,
            rules_text_enriched=version.rules_text_enriched,
            rules_text=render_enriched_rule_text(
                version.rules_text_enriched,
                symbol_tokens_by_key=symbol_tokens_by_key,
            ),
            confidence=version.confidence,
            field_sources_json=version.field_sources,
            parsed_snapshot_json=version.parsed_snapshot,
            is_latest=version.is_latest,
            content_version=content_version,
        )
    return version_models


def _import_card_version_relations(
    card_record: DeveloperDataCardRecord,
    *,
    version_models: dict[int, CardVersion],
    catalogs: _ImportedCatalogs,
) -> None:
    for version in card_record.versions:
        model = version_models[version.version_number]
        if version.previous_version_number is not None:
            model.previous_version = version_models[version.previous_version_number]
            model.save(update_fields=["previous_version"])
        _import_card_version_images(version, model)
        _import_card_version_catalog_links(version, model, catalogs)


def _import_card_version_images(version: Any, model: CardVersion) -> None:
    images = []
    for image in version.images:
        images.append(
            CardVersionImage(
                card_version=model,
                source_file=image.stored_path,
                stored_path=image.stored_path,
                width=image.width,
                height=image.height,
                checksum=image.checksum,
            )
        )
    CardVersionImage.objects.bulk_create(images)


def _import_card_version_catalog_links(
    version: Any,
    model: CardVersion,
    catalogs: _ImportedCatalogs,
) -> None:
    keyword_links = []
    for key in version.keyword_keys:
        keyword_links.append(CardVersionKeyword(card_version=model, keyword=catalogs.keywords[key]))
    CardVersionKeyword.objects.bulk_create(keyword_links)

    tag_links = []
    for key in version.tag_keys:
        tag_links.append(CardVersionTag(card_version=model, tag=catalogs.tags[key]))
    CardVersionTag.objects.bulk_create(tag_links)

    symbol_links = []
    for key in version.symbol_keys:
        symbol_links.append(CardVersionSymbol(card_version=model, symbol=catalogs.symbols[key]))
    CardVersionSymbol.objects.bulk_create(symbol_links)

    type_links = []
    for key in version.type_keys:
        type_links.append(CardVersionType(card_version=model, type=catalogs.types[key]))
    CardVersionType.objects.bulk_create(type_links)


def _import_card_groups(
    payload: DeveloperDataPayload,
    cards: dict[CardReferenceIdentity, Card],
) -> None:
    for group_record in payload.card_groups:
        group = CardGroup.objects.create(
            key=group_record.key,
            name=group_record.name,
            anchor_card=cards[card_reference_identity(group_record.anchor_card_ref)],
        )
        members = []
        for member in group_record.members:
            members.append(
                CardGroupMember(
                    group=group,
                    card=cards[card_reference_identity(member.card_ref)],
                    position=member.position,
                )
            )
        CardGroupMember.objects.bulk_create(members)
def _create_catalog_rows(model: Any, rows: list[Any]) -> dict[str, Any]:
    catalog: dict[str, Any] = {}
    for row in rows:
        instance, _created = model.objects.update_or_create(
            key=row.key,
            defaults={
                "label": row.label,
                "identifiers_json": row.identifiers,
            },
        )
        catalog[row.key] = instance
    return catalog


def _symbol_reference_asset_path(stored_path: str) -> str:
    prefix = "symbols/"
    if not stored_path.startswith(prefix) or stored_path == prefix:
        raise DeveloperDataError(
            f"Developer-data symbol asset must be stored under symbols/: {stored_path}"
        )
    return stored_path.removeprefix(prefix)


def _validate_payload_references(payload: DeveloperDataPayload) -> None:
    issues = validate_import_readiness(payload)
    references = _payload_reference_sets(payload)
    _validate_card_back_references(payload, references.card_back_checksums, issues)
    _validate_classification_rule_references(payload, references, issues)
    _validate_symbol_asset_references(payload)
    card_identities = _validate_card_references(payload, references, issues)
    _validate_card_group_references(payload, card_identities, issues)
    if issues:
        raise DeveloperDataError("Developer-data payload failed validation: " + "; ".join(issues))


@dataclass(frozen=True)
class _PayloadReferenceSets:
    keyword_keys: set[str]
    tag_keys: set[str]
    type_keys: set[str]
    symbol_keys: set[str]
    template_keys: set[str]
    content_versions: set[str]
    card_back_checksums: set[str]


def _payload_reference_sets(payload: DeveloperDataPayload) -> _PayloadReferenceSets:
    return _PayloadReferenceSets(
        keyword_keys={row.key for row in payload.keywords},
        tag_keys={row.key for row in payload.tags},
        type_keys={row.key for row in payload.types},
        symbol_keys={row.key for row in payload.symbols},
        template_keys={row.key for row in payload.templates},
        content_versions={row.version_number for row in payload.content_versions},
        card_back_checksums={row.checksum for row in payload.card_backs},
    )


def _validate_card_back_references(
    payload: DeveloperDataPayload,
    card_back_checksums: set[str],
    issues: list[str],
) -> None:
    if len(card_back_checksums) != len(payload.card_backs):
        issues.append("card-back checksums are not unique")

    default_pools = [row.card_pool for row in payload.card_back_pool_defaults]
    if len(default_pools) != len(set(default_pools)):
        issues.append("card-back pool defaults are not unique")
    if set(default_pools) != {"player", "evil", "neutral"}:
        issues.append("card-back pool defaults must include player, evil, and neutral")

    for pool_default in payload.card_back_pool_defaults:
        if (
            pool_default.card_back_checksum is not None
            and pool_default.card_back_checksum not in card_back_checksums
        ):
            issues.append(
                f"{pool_default.card_pool} default references an unknown card back"
            )

    default_factions = [row.faction for row in payload.card_back_faction_defaults]
    if len(default_factions) != len(set(default_factions)):
        issues.append("card-back faction defaults are not unique")
    if set(default_factions) != set(CARD_FACTIONS):
        issues.append("card-back faction defaults must include every Evil faction")

    for faction_default in payload.card_back_faction_defaults:
        if (
            faction_default.card_back_checksum is not None
            and faction_default.card_back_checksum not in card_back_checksums
        ):
            issues.append(
                f"{faction_default.faction} faction default references an unknown card back"
            )

    default_roles = [row.role for row in payload.card_back_role_defaults]
    if len(default_roles) != len(set(default_roles)):
        issues.append("card-back role defaults are not unique")
    if set(default_roles) != set(CARD_ROLES):
        issues.append("card-back role defaults must include every persisted role")

    for role_default in payload.card_back_role_defaults:
        if (
            role_default.card_back_checksum is not None
            and role_default.card_back_checksum not in card_back_checksums
        ):
            issues.append(
                f"{role_default.role} role default references an unknown card back"
            )


def _validate_classification_rule_references(
    payload: DeveloperDataPayload,
    references: _PayloadReferenceSets,
    issues: list[str],
) -> None:
    targets_by_kind = {
        "role": CARD_ROLES,
        "faction": CARD_FACTIONS,
        "mana_family": tuple(MANA_FAMILY_BY_KEY),
    }
    sources_by_kind = {
        "tag": references.tag_keys,
        "type": references.type_keys,
        "symbol": references.symbol_keys,
    }
    rule_identities: set[tuple[str, str, str, str, str]] = set()
    for rule in payload.classification_rules:
        identity = (
            rule.card_pool,
            rule.target_kind,
            rule.target_key,
            rule.source_kind,
            rule.source_key,
        )
        if identity in rule_identities:
            issues.append("classification rule identities are not unique")
        rule_identities.add(identity)
        available_targets = targets_by_kind[rule.target_kind]
        if rule.target_key not in available_targets:
            issues.append(
                f"classification rule references unknown {rule.target_kind} {rule.target_key}"
            )
        available_sources = sources_by_kind[rule.source_kind]
        if rule.source_key not in available_sources:
            issues.append(
                f"classification rule references unknown {rule.source_kind} {rule.source_key}"
            )


def _validate_symbol_asset_references(payload: DeveloperDataPayload) -> None:
    for symbol in payload.symbols:
        for asset_path in symbol.reference_assets:
            _symbol_reference_asset_path(asset_path)


def _validate_card_references(
    payload: DeveloperDataPayload,
    references: _PayloadReferenceSets,
    issues: list[str],
) -> set[CardReferenceIdentity]:
    card_identities = {_payload_card_identity(row) for row in payload.cards}
    if len(card_identities) != len(payload.cards):
        issues.append("card identities are not unique")

    for card in payload.cards:
        if (
            card.card_back_override_checksum is not None
            and card.card_back_override_checksum not in references.card_back_checksums
        ):
            issues.append(f"card {card.key} references an unknown card back override")
        _validate_card_version_references(card, references, issues)
    return card_identities


def _validate_card_version_references(
    card: DeveloperDataCardRecord,
    references: _PayloadReferenceSets,
    issues: list[str],
) -> None:
    version_numbers = {version.version_number for version in card.versions}
    latest_markers = []
    for version in card.versions:
        if version.is_latest:
            latest_markers.append(version.version_number)

    no_versions_expected = (
        card.latest_version_number is None
        and not version_numbers
        and not latest_markers
    )
    selected_latest_is_valid = (
        card.latest_version_number in version_numbers
        and latest_markers == [card.latest_version_number]
    )
    if not no_versions_expected and not selected_latest_is_valid:
        issues.append(f"card {card.key} has an invalid latest version")

    for version in card.versions:
        if version.template_key not in references.template_keys:
            issues.append(f"card {card.key} references unknown template {version.template_key}")
        if (
            version.previous_version_number is not None
            and version.previous_version_number not in version_numbers
        ):
            issues.append(f"card {card.key} has an invalid previous version")
        if (
            version.content_version_number is not None
            and version.content_version_number not in references.content_versions
        ):
            issues.append(f"card {card.key} references an unknown content version")
        _append_missing_reference_issue(
            issues,
            card.key,
            "keywords",
            version.keyword_keys,
            references.keyword_keys,
        )
        _append_missing_reference_issue(
            issues,
            card.key,
            "tags",
            version.tag_keys,
            references.tag_keys,
        )
        _append_missing_reference_issue(
            issues,
            card.key,
            "symbols",
            version.symbol_keys,
            references.symbol_keys,
        )
        _append_missing_reference_issue(
            issues,
            card.key,
            "types",
            version.type_keys,
            references.type_keys,
        )


def _validate_card_group_references(
    payload: DeveloperDataPayload,
    card_identities: set[CardReferenceIdentity],
    issues: list[str],
) -> None:
    for group in payload.card_groups:
        referenced = {card_reference_identity(group.anchor_card_ref)}
        for member in group.members:
            referenced.add(card_reference_identity(member.card_ref))
        missing = sorted(referenced - card_identities)
        if missing:
            missing_labels = []
            for reference in missing:
                missing_labels.append(_card_reference_label(reference))
            joined_labels = ", ".join(missing_labels)
            issues.append(f"group {group.key} references unknown cards: {joined_labels}")


def _card_reference_label(
    reference: CardReferenceIdentity,
) -> str:
    card_pool, card_factions, key = reference
    factions = ",".join(str(faction) for faction in card_factions) or "none"
    return f"{card_pool}/{factions}/{key}"


def _payload_card_identity(card: DeveloperDataCardRecord) -> CardReferenceIdentity:
    return card_reference_identity(
        CardReferenceRecord(
            key=card.key,
            card_pool=card.card_pool,
            card_factions=card.card_factions,
            card_mana_families=card.card_mana_families,
        )
    )


def _append_missing_reference_issue(
    issues: list[str],
    card_key: str,
    label: str,
    values: list[str],
    available: set[str],
) -> None:
    missing = sorted(set(values) - available)
    if missing:
        issues.append(f"card {card_key} references unknown {label}: {', '.join(missing)}")


def _validate_payload_assets(
    *,
    payload: DeveloperDataPayload,
    manifest: DeveloperDataManifest,
) -> set[str]:
    asset_checksums = {
        entry.path.removeprefix("assets/"): entry.sha256
        for entry in manifest.files
        if entry.path.startswith("assets/")
    }
    image_assets = {
        image.stored_path
        for card in payload.cards
        for version in card.versions
        for image in version.images
    }
    image_assets.update(card_back.stored_path for card_back in payload.card_backs)
    symbol_assets = {asset for symbol in payload.symbols for asset in symbol.reference_assets}
    invalid_roots = sorted(
        path for path in image_assets if not _is_asset_under_root(path, expected_root="images")
    )
    invalid_roots.extend(
        sorted(
            path
            for path in symbol_assets
            if not _is_asset_under_root(path, expected_root="symbols")
        )
    )
    if invalid_roots:
        raise DeveloperDataError(
            "Developer-data payload references assets outside public storage roots: "
            + ", ".join(invalid_roots)
        )
    referenced_assets = image_assets | symbol_assets
    missing = sorted(referenced_assets - set(asset_checksums))
    if missing:
        raise DeveloperDataError(
            "Developer-data payload references assets missing from the manifest: "
            + ", ".join(missing)
        )
    unreferenced = sorted(set(asset_checksums) - referenced_assets)
    if unreferenced:
        raise DeveloperDataError(
            "Developer-data manifest contains unreferenced assets: " + ", ".join(unreferenced)
        )
    return referenced_assets


def _is_asset_under_root(stored_path: str, *, expected_root: str) -> bool:
    parts = PurePosixPath(stored_path).parts
    return (
        len(parts) > 1
        and parts[0] == expected_root
        and all(part not in {".", ".."} for part in parts)
    )

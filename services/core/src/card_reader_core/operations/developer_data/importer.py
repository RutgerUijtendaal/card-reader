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
from card_reader_core.services.classification_rules import (
    ClassificationRuleService,
    ensure_default_mana_family_classification_rules,
)
from card_reader_core.services.templates import apply_bundled_template_compatibility
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
    if not payload.keywords:
        issues.append("keyword catalog is empty")
    if not payload.tags:
        issues.append("tag catalog is empty")
    if not payload.types:
        issues.append("type catalog is empty")
    if not payload.symbols:
        issues.append("symbol catalog is empty")
    if not payload.templates:
        issues.append("template catalog is empty")
    if not payload.deck_tags:
        issues.append("deck-tag catalog is empty")
    if not payload.cards:
        issues.append("card selection is empty")
    if not any(
        card.card_pool == "player"
        and "hero" in card.card_roles
        and card.lifecycle_status == "active"
        for card in payload.cards
    ):
        issues.append("no active hero is included")
    if not any(
        "hero" not in card.card_roles
        and card.card_pool == "player"
        and card.lifecycle_status == "active"
        for card in payload.cards
    ):
        issues.append("no active mainboard cards are included")
    if payload.current_card_back is None:
        issues.append("current card back is missing")
    return issues


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
    keywords = _create_catalog_rows(Keyword, payload.keywords)
    tags = _create_catalog_rows(Tag, payload.tags)
    types = _create_catalog_rows(Type, payload.types)
    symbols = {
        row.key: Symbol.objects.create(
            key=row.key,
            label=row.label,
            symbol_type=row.symbol_type,
            detector_type=row.detector_type,
            detection_config_json=row.detection_config,
            text_enrichment_json=row.text_enrichment,
            reference_assets_json=[
                _symbol_reference_asset_path(asset_path) for asset_path in row.reference_assets
            ],
            text_token=row.text_token,
            enabled=row.enabled,
        )
        for row in payload.symbols
    }
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
    classification_rule_service = ClassificationRuleService()
    for rule_record in payload.classification_rules:
        source_rows = {
            "tag": tags,
            "type": types,
            "symbol": symbols,
        }[rule_record.source_kind]
        source = source_rows[rule_record.source_key]
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
            classification_rule_service.create_rule(
                card_pool=rule_record.card_pool,
                target_kind=rule_record.target_kind,
                target_key=rule_record.target_key,
                source_kind=rule_record.source_kind,
                source_id=source.id,
                enabled=rule_record.enabled,
            )
        elif existing_rule.enabled != rule_record.enabled:
            classification_rule_service.update_rule(
                rule_id=existing_rule.id,
                enabled=rule_record.enabled,
            )
    if source_format_version in {1, 2}:
        ensure_default_mana_family_classification_rules()
    for deck_tag_record in payload.deck_tags:
        DeckTag.objects.update_or_create(
            kind=deck_tag_record.kind,
            key=deck_tag_record.key,
            defaults={"label": deck_tag_record.label},
        )
    content_versions = {
        row.version_number: ContentVersion.objects.create(
            version_number=row.version_number,
            base_version=row.base_version,
            major=row.major,
            minor=row.minor,
            patch=row.patch,
            description=row.description,
        )
        for row in payload.content_versions
    }
    cards = {
        _payload_card_identity(row): Card.objects.create(
            key=row.key,
            label=row.label,
            card_pool=row.card_pool,
            faction_identity_key=card_faction_identity_key(row.card_factions),
            deck_building_config_json=row.deck_building_config,
            lifecycle_status=row.lifecycle_status,
        )
        for row in payload.cards
    }
    for card_record in payload.cards:
        card = cards[_payload_card_identity(card_record)]
        CardRoleAssignment.objects.bulk_create(
            [CardRoleAssignment(card=card, role=role) for role in card_record.card_roles]
        )
        CardFactionAssignment.objects.bulk_create(
            [
                CardFactionAssignment(card=card, faction=faction)
                for faction in card_record.card_factions
            ]
        )
        set_card_mana_families(
            card=card,
            mana_families=card_record.card_mana_families,
        )
        CardAlias.objects.bulk_create(
            [
                CardAlias(
                    card=card,
                    card_pool=card.card_pool,
                    faction_identity_key=card.faction_identity_key,
                    key=alias.key,
                    label=alias.label,
                )
                for alias in card_record.aliases
            ]
        )
        version_models: dict[int, CardVersion] = {}
        for version in card_record.versions:
            version_models[version.version_number] = CardVersion.objects.create(
                card=card,
                version_number=version.version_number,
                template=templates[version.template_key],
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
                rules_text=version.rules_text,
                confidence=version.confidence,
                field_sources_json=version.field_sources,
                parsed_snapshot_json=version.parsed_snapshot,
                is_latest=version.is_latest,
                content_version=(
                    content_versions[version.content_version_number]
                    if version.content_version_number is not None
                    else None
                ),
            )
        for version in card_record.versions:
            model = version_models[version.version_number]
            if version.previous_version_number is not None:
                model.previous_version = version_models[version.previous_version_number]
                model.save(update_fields=["previous_version"])
            CardVersionImage.objects.bulk_create(
                [
                    CardVersionImage(
                        card_version=model,
                        source_file=image.stored_path,
                        stored_path=image.stored_path,
                        width=image.width,
                        height=image.height,
                        checksum=image.checksum,
                    )
                    for image in version.images
                ]
            )
            CardVersionKeyword.objects.bulk_create(
                [
                    CardVersionKeyword(card_version=model, keyword=keywords[key])
                    for key in version.keyword_keys
                ]
            )
            CardVersionTag.objects.bulk_create(
                [CardVersionTag(card_version=model, tag=tags[key]) for key in version.tag_keys]
            )
            CardVersionSymbol.objects.bulk_create(
                [
                    CardVersionSymbol(card_version=model, symbol=symbols[key])
                    for key in version.symbol_keys
                ]
            )
            CardVersionType.objects.bulk_create(
                [CardVersionType(card_version=model, type=types[key]) for key in version.type_keys]
            )
        if card_record.latest_version_number is not None:
            card.latest_version = version_models[card_record.latest_version_number]
            card.save(update_fields=["latest_version"])

    for group_record in payload.card_groups:
        group = CardGroup.objects.create(
            key=group_record.key,
            name=group_record.name,
            anchor_card=cards[card_reference_identity(group_record.anchor_card_ref)],
        )
        CardGroupMember.objects.bulk_create(
            [
                CardGroupMember(
                    group=group,
                    card=cards[card_reference_identity(member.card_ref)],
                    position=member.position,
                )
                for member in group_record.members
            ]
        )
    if payload.current_card_back is not None:
        card_back_record = payload.current_card_back
        CardBack.objects.create(
            label=card_back_record.label,
            original_filename=Path(card_back_record.stored_path).name,
            source_file=card_back_record.stored_path,
            stored_path=card_back_record.stored_path,
            width=card_back_record.width,
            height=card_back_record.height,
            checksum=card_back_record.checksum,
            is_current=True,
        )


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
    keyword_keys = {row.key for row in payload.keywords}
    tag_keys = {row.key for row in payload.tags}
    type_keys = {row.key for row in payload.types}
    symbol_keys = {row.key for row in payload.symbols}
    template_keys = {row.key for row in payload.templates}
    content_versions = {row.version_number for row in payload.content_versions}
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
        available_targets = (
            CARD_ROLES
            if rule.target_kind == "role"
            else CARD_FACTIONS
            if rule.target_kind == "faction"
            else tuple(MANA_FAMILY_BY_KEY)
        )
        if rule.target_key not in available_targets:
            issues.append(
                f"classification rule references unknown {rule.target_kind} {rule.target_key}"
            )
        available_sources = (
            tag_keys
            if rule.source_kind == "tag"
            else type_keys
            if rule.source_kind == "type"
            else symbol_keys
        )
        if rule.source_key not in available_sources:
            issues.append(
                f"classification rule references unknown {rule.source_kind} {rule.source_key}"
            )
    card_identities = {_payload_card_identity(row) for row in payload.cards}
    if len(card_identities) != len(payload.cards):
        issues.append("card identities are not unique")
    for symbol in payload.symbols:
        for asset_path in symbol.reference_assets:
            _symbol_reference_asset_path(asset_path)
    for card in payload.cards:
        version_numbers = {version.version_number for version in card.versions}
        latest_markers = [
            version.version_number for version in card.versions if version.is_latest
        ]
        valid_latest_version = (
            card.latest_version_number is None
            and not version_numbers
            and not latest_markers
        ) or (
            card.latest_version_number in version_numbers
            and latest_markers == [card.latest_version_number]
        )
        if not valid_latest_version:
            issues.append(f"card {card.key} has an invalid latest version")
        for version in card.versions:
            if version.template_key not in template_keys:
                issues.append(f"card {card.key} references unknown template {version.template_key}")
            if (
                version.previous_version_number is not None
                and version.previous_version_number not in version_numbers
            ):
                issues.append(f"card {card.key} has an invalid previous version")
            if (
                version.content_version_number is not None
                and version.content_version_number not in content_versions
            ):
                issues.append(f"card {card.key} references an unknown content version")
            _append_missing_reference_issue(
                issues, card.key, "keywords", version.keyword_keys, keyword_keys
            )
            _append_missing_reference_issue(issues, card.key, "tags", version.tag_keys, tag_keys)
            _append_missing_reference_issue(
                issues, card.key, "symbols", version.symbol_keys, symbol_keys
            )
            _append_missing_reference_issue(issues, card.key, "types", version.type_keys, type_keys)
    for group in payload.card_groups:
        referenced = {
            card_reference_identity(group.anchor_card_ref),
            *(card_reference_identity(member.card_ref) for member in group.members),
        }
        missing = sorted(referenced - card_identities)
        if missing:
            missing_labels = ", ".join(_card_reference_label(reference) for reference in missing)
            issues.append(f"group {group.key} references unknown cards: {missing_labels}")
    if issues:
        raise DeveloperDataError("Developer-data payload failed validation: " + "; ".join(issues))


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
    if payload.current_card_back is not None:
        image_assets.add(payload.current_card_back.stored_path)
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

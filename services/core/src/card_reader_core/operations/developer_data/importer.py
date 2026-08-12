from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import shutil
from typing import Any

from django.db import transaction

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    Card,
    CardAlias,
    CardBack,
    CardGroup,
    CardGroupMember,
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
)
from card_reader_core.metadata import mana_family_sort_key

from .archive import DeveloperDataError, extracted_archive, load_extracted_bundle, sha256_file
from .schema import DeveloperDataManifest, DeveloperDataPayload


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
        actual_archive_sha256 = sha256_file(archive_path)
        if actual_archive_sha256 != expected_archive_sha256:
            raise DeveloperDataError("Developer-data archive checksum does not match the lock file.")
    with extracted_archive(archive_path) as extraction_root:
        manifest, payload = load_extracted_bundle(extraction_root)
        if expected_bundle_version is not None and manifest.bundle_version != expected_bundle_version:
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
                _import_payload(payload)
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
        CardGroup,
        ContentVersion,
        Keyword,
        Symbol,
        Tag,
        Template,
        TtsCardSheet,
        Type,
    ):
        if model.objects.exists():
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
            raise DeveloperDataError(f"Asset target escapes storage root: {relative_storage_path}") from exc
        if target.exists():
            if not target.is_file() or target.stat().st_size != entry.size_bytes or sha256_file(target) != entry.sha256:
                raise DeveloperDataError(f"Conflicting local asset already exists: {relative_storage_path}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        created.append(target)


def _import_payload(payload: DeveloperDataPayload) -> None:
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
                _symbol_reference_asset_path(asset_path)
                for asset_path in row.reference_assets
            ],
            text_token=row.text_token,
            enabled=row.enabled,
        )
        for row in payload.symbols
    }
    templates = {
        row.key: Template.objects.create(
            key=row.key,
            label=row.label,
            definition_json=row.definition,
            inferred_card_roles_json=row.inferred_card_roles,
        )
        for row in payload.templates
    }
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
        row.key: Card.objects.create(
            key=row.key,
            label=row.label,
            card_pool=row.card_pool,
            deck_building_config_json=row.deck_building_config,
            lifecycle_status=row.lifecycle_status,
        )
        for row in payload.cards
    }
    for card_record in payload.cards:
        card = cards[card_record.key]
        CardRoleAssignment.objects.bulk_create(
            [CardRoleAssignment(card=card, role=role) for role in card_record.card_roles]
        )
        CardAlias.objects.bulk_create(
            [
                CardAlias(
                    card=card,
                    card_pool=card.card_pool,
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
                mana_family_sort_key=mana_family_sort_key(version.symbol_keys),
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
                [CardVersionKeyword(card_version=model, keyword=keywords[key]) for key in version.keyword_keys]
            )
            CardVersionTag.objects.bulk_create(
                [CardVersionTag(card_version=model, tag=tags[key]) for key in version.tag_keys]
            )
            CardVersionSymbol.objects.bulk_create(
                [CardVersionSymbol(card_version=model, symbol=symbols[key]) for key in version.symbol_keys]
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
            anchor_card=cards[group_record.anchor_card_key],
        )
        CardGroupMember.objects.bulk_create(
            [
                CardGroupMember(group=group, card=cards[member.card_key], position=member.position)
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
    return {
        row.key: model.objects.create(
            key=row.key,
            label=row.label,
            identifiers_json=row.identifiers,
        )
        for row in rows
    }


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
    card_keys = {row.key for row in payload.cards}
    if len(card_keys) != len(payload.cards):
        issues.append("card keys are not unique")
    for symbol in payload.symbols:
        for asset_path in symbol.reference_assets:
            _symbol_reference_asset_path(asset_path)
    for card in payload.cards:
        version_numbers = {version.version_number for version in card.versions}
        if card.latest_version_number not in version_numbers:
            issues.append(f"card {card.key} has an invalid latest version")
        for version in card.versions:
            if version.template_key not in template_keys:
                issues.append(f"card {card.key} references unknown template {version.template_key}")
            if version.previous_version_number is not None and version.previous_version_number not in version_numbers:
                issues.append(f"card {card.key} has an invalid previous version")
            if version.content_version_number is not None and version.content_version_number not in content_versions:
                issues.append(f"card {card.key} references an unknown content version")
            _append_missing_reference_issue(issues, card.key, "keywords", version.keyword_keys, keyword_keys)
            _append_missing_reference_issue(issues, card.key, "tags", version.tag_keys, tag_keys)
            _append_missing_reference_issue(issues, card.key, "symbols", version.symbol_keys, symbol_keys)
            _append_missing_reference_issue(issues, card.key, "types", version.type_keys, type_keys)
    for group in payload.card_groups:
        referenced = {group.anchor_card_key, *(member.card_key for member in group.members)}
        missing = sorted(referenced - card_keys)
        if missing:
            issues.append(f"group {group.key} references unknown cards: {', '.join(missing)}")
    if issues:
        raise DeveloperDataError("Developer-data payload failed validation: " + "; ".join(issues))


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
            "Developer-data payload references assets missing from the manifest: " + ", ".join(missing)
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

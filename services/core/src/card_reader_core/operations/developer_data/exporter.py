from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from typing import Any, cast

from django.db.migrations.recorder import MigrationRecorder
from card_reader_core.config.settings import settings
from card_reader_core.models import (
    CARD_CLASSIFICATION_SOURCE_TAG,
    CARD_CLASSIFICATION_SOURCE_TYPE,
    CARD_CLASSIFICATION_TARGET_ROLE,
    CARD_CLASSIFICATION_TARGET_FACTION,
    CARD_FACTION_DEFINITIONS,
    CARD_POOL_DEFINITIONS,
    CARD_POOLS,
    CARD_ROLE_DEFINITIONS,
    PLAYER_CARD_POOL,
    Card,
    CardBack,
    CardClassificationRule,
    CardGroup,
    ContentVersion,
    DeckTag,
    Keyword,
    Symbol,
    Tag,
    Template,
    Type,
    CardPool,
    card_faction_keys,
    card_mana_family_keys,
    card_role_keys,
)
from card_reader_core.metadata import MANA_FAMILIES
from card_reader_core.storage import (
    calculate_checksum,
    relativize_image_storage_path,
    relativize_storage_path,
)

from .archive import DeveloperDataError, canonical_json_bytes
from .schema import (
    DEVELOPER_DATA_FORMAT_VERSION,
    BundleFileRecord,
    CardAliasRecord,
    CardBackRecord,
    CardBackPoolDefaultRecord,
    CardGroupMemberRecord,
    CardGroupRecord,
    CardImageRecord,
    CardRecord,
    CardReferenceRecord,
    CardVersionRecord,
    CatalogRecord,
    ClassificationRuleRecord,
    ContentVersionRecord,
    DeckTagRecord,
    DeveloperDataManifest,
    DeveloperDataPayload,
    DeveloperDataSelection,
    SymbolRecord,
    TemplateRecord,
)
from card_reader_core.services.card_backs import get_pool_card_back_defaults

DEVELOPER_DATA_CARD_POOL = PLAYER_CARD_POOL
DEVELOPER_DATA_EXCLUDED_POOLS = tuple(
    pool for pool in CARD_POOLS if pool != DEVELOPER_DATA_CARD_POOL
)


def export_developer_data(
    *,
    selection_path: Path,
    output_path: Path,
    source_revision: str = "unknown",
    bundle_version: str | None = None,
) -> DeveloperDataManifest:
    selection_bytes = selection_path.read_bytes()
    try:
        selection = DeveloperDataSelection.model_validate_json(selection_bytes)
    except Exception as exc:
        raise DeveloperDataError(f"Developer-data selection is invalid: {selection_path}") from exc
    if output_path.exists():
        raise DeveloperDataError(
            f"Refusing to overwrite existing developer-data archive: {output_path}"
        )

    cards, groups = _resolve_selection(selection)
    payload = _build_payload(cards=cards, groups=groups)
    _validate_payload_sanitization(payload)
    _validate_coverage(selection, payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="card-reader-dev-data-export-") as temp_value:
        staging_root = Path(temp_value) / "bundle"
        staging_root.mkdir(parents=True)
        data_path = staging_root / "data.json"
        data_path.write_bytes(canonical_json_bytes(payload.model_dump(mode="json")))
        _copy_payload_assets(payload, staging_root=staging_root)

        files = _build_file_manifest(staging_root)
        manifest = DeveloperDataManifest(
            format_version=DEVELOPER_DATA_FORMAT_VERSION,
            bundle_version=bundle_version or selection.bundle_version,
            created_at=datetime.now(UTC),
            source_revision=source_revision,
            source_migration=_latest_core_migration(),
            selection_sha256=_sha256_bytes(selection_bytes),
            counts=_payload_counts(payload),
            files=files,
        )
        (staging_root / "manifest.json").write_bytes(
            canonical_json_bytes(manifest.model_dump(mode="json"))
        )
        temp_archive = output_path.with_name(f".{output_path.name}.tmp")
        try:
            with tarfile.open(temp_archive, "w:gz") as archive:
                for path in sorted(staging_root.rglob("*")):
                    archive.add(path, arcname=path.relative_to(staging_root).as_posix())
            temp_archive.replace(output_path)
        finally:
            temp_archive.unlink(missing_ok=True)
    return manifest


def _resolve_selection(
    selection: DeveloperDataSelection,
) -> tuple[list[Card], list[CardGroup]]:
    selected_keys = set(selection.card_keys)
    group_card_ids: set[str] = set()
    group_queryset = CardGroup.objects.filter(
        anchor_card__card_pool=DEVELOPER_DATA_CARD_POOL,
    ).exclude(members__card__card_pool__in=DEVELOPER_DATA_EXCLUDED_POOLS)
    if not selection.include_all_card_groups:
        group_queryset = group_queryset.filter(key__in=selection.card_group_keys)
    groups = list(
        group_queryset.select_related("anchor_card")
        .prefetch_related("members__card")
        .order_by("key")
    )
    missing_groups = sorted(set(selection.card_group_keys) - {group.key for group in groups})
    if missing_groups:
        raise DeveloperDataError(
            f"Selected card groups were not found: {', '.join(missing_groups)}"
        )
    for group in groups:
        group_card_ids.add(group.anchor_card.id)
        group_card_ids.update(member.card.id for member in group.members.all())

    card_queryset = Card.objects.filter(card_pool=DEVELOPER_DATA_CARD_POOL)
    explicit_matches: dict[str, list[str]] = {}
    for card_id, card_key in card_queryset.filter(key__in=selected_keys).values_list("id", "key"):
        explicit_matches.setdefault(card_key, []).append(card_id)
    missing_cards = sorted(selected_keys - explicit_matches.keys())
    if missing_cards:
        raise DeveloperDataError(f"Selected cards were not found: {', '.join(missing_cards)}")
    ambiguous_cards = sorted(
        card_key for card_key, card_ids in explicit_matches.items() if len(card_ids) > 1
    )
    if ambiguous_cards:
        raise DeveloperDataError(
            "Selected card keys are ambiguous across faction namespaces: "
            f"{', '.join(ambiguous_cards)}"
        )
    if not selection.include_all_cards:
        selected_card_ids = group_card_ids | {card_ids[0] for card_ids in explicit_matches.values()}
        card_queryset = card_queryset.filter(id__in=selected_card_ids)
    cards = list(
        card_queryset.select_related("card_back_override").prefetch_related(
            "role_assignments",
            "faction_assignments",
            "mana_family_assignments",
            "aliases",
            "versions__template",
            "versions__content_version",
            "versions__images",
            "versions__card_version_keywords__keyword",
            "versions__card_version_tags__tag",
            "versions__card_version_symbols__symbol",
            "versions__card_version_types__type",
        ).order_by("key", "faction_identity_key", "id")
    )
    return cards, groups


def _build_payload(*, cards: list[Card], groups: list[CardGroup]) -> DeveloperDataPayload:
    content_version_numbers = {
        version.content_version.version_number
        for card in cards
        for version in card.versions.all()
        if version.content_version is not None
    }
    pool_defaults = get_pool_card_back_defaults()
    referenced_card_back_ids = {
        card_back.id for card_back in pool_defaults.values() if card_back is not None
    }
    referenced_card_back_ids.update(
        card.card_back_override.id
        for card in cards
        if card.card_back_override is not None
    )
    card_backs_by_checksum: dict[str, CardBack] = {}
    for card_back in CardBack.objects.filter(id__in=referenced_card_back_ids).order_by(
        "checksum", "id"
    ):
        card_backs_by_checksum.setdefault(card_back.checksum, card_back)
    card_backs = list(card_backs_by_checksum.values())
    return DeveloperDataPayload(
        keywords=[_catalog_record(row) for row in Keyword.objects.order_by("key")],
        tags=[_catalog_record(row) for row in Tag.objects.order_by("key")],
        types=[_catalog_record(row) for row in Type.objects.order_by("key")],
        symbols=[_symbol_record(row) for row in Symbol.objects.order_by("key")],
        templates=[
            TemplateRecord(
                key=row.key,
                label=row.label,
                definition=row.definition_json,
            )
            for row in Template.objects.order_by("key")
        ],
        classification_rules=sorted(
            (
                _classification_rule_record(row)
                for row in CardClassificationRule.objects.select_related(
                    "tag", "type", "symbol"
                )
            ),
            key=_classification_rule_sort_key,
        ),
        deck_tags=[
            DeckTagRecord(kind=row.kind, key=row.key, label=row.label)
            for row in DeckTag.objects.order_by("kind", "key")
        ],
        content_versions=[
            ContentVersionRecord(
                version_number=row.version_number,
                base_version=row.base_version,
                major=row.major,
                minor=row.minor,
                patch=row.patch,
                description=row.description,
            )
            for row in ContentVersion.objects.filter(
                version_number__in=content_version_numbers
            ).order_by("major", "minor", "patch")
        ],
        cards=[_card_record(card) for card in cards],
        card_groups=[_group_record(group) for group in groups],
        card_backs=[_card_back_record(card_back) for card_back in card_backs],
        card_back_pool_defaults=[
            CardBackPoolDefaultRecord(
                card_pool=card_pool,
                card_back_checksum=_optional_card_back_checksum(pool_defaults[card_pool]),
            )
            for card_pool in CARD_POOLS
        ],
    )


def _classification_rule_record(
    row: CardClassificationRule,
) -> ClassificationRuleRecord:
    source = (
        row.tag
        if row.source_kind == "tag"
        else row.type
        if row.source_kind == "type"
        else row.symbol
    )
    if source is None:
        raise DeveloperDataError(f"Classification rule {row.id} has no source.")
    return ClassificationRuleRecord(
        card_pool=cast(CardPool, row.card_pool),
        target_kind=row.target_kind,
        target_key=row.target_key,
        source_kind=row.source_kind,
        source_key=source.key,
        enabled=row.enabled,
    )


def _classification_rule_sort_key(
    rule: ClassificationRuleRecord,
) -> tuple[int, int, int, int, str]:
    pool_rank = next(
        definition.rank for definition in CARD_POOL_DEFINITIONS if definition.key == rule.card_pool
    )
    if rule.target_kind == CARD_CLASSIFICATION_TARGET_ROLE:
        target_kind_rank = 0
        target_rank = next(
            definition.rank
            for definition in CARD_ROLE_DEFINITIONS
            if definition.key == rule.target_key
        )
    elif rule.target_kind == CARD_CLASSIFICATION_TARGET_FACTION:
        target_kind_rank = 1
        target_rank = next(
            definition.rank
            for definition in CARD_FACTION_DEFINITIONS
            if definition.key == rule.target_key
        )
    else:
        target_kind_rank = 2
        target_rank = next(
            definition.rank
            for definition in MANA_FAMILIES
            if definition.key == rule.target_key
        )
    source_kind_rank = (
        0
        if rule.source_kind == CARD_CLASSIFICATION_SOURCE_TAG
        else 1
        if rule.source_kind == CARD_CLASSIFICATION_SOURCE_TYPE
        else 2
    )
    return pool_rank, target_kind_rank, target_rank, source_kind_rank, rule.source_key


def _catalog_record(row: Keyword | Tag | Type) -> CatalogRecord:
    return CatalogRecord(key=row.key, label=row.label, identifiers=list(row.identifiers_json))


def _symbol_record(row: Symbol) -> SymbolRecord:
    return SymbolRecord(
        key=row.key,
        label=row.label,
        symbol_type=row.symbol_type,
        detector_type=row.detector_type,
        detection_config=dict(row.detection_config_json),
        text_enrichment=dict(row.text_enrichment_json),
        reference_assets=[
            _normalize_symbol_asset_path(value) for value in row.reference_assets_json
        ],
        text_token=row.text_token,
        enabled=row.enabled,
    )


def _normalize_symbol_asset_path(value: object) -> str:
    if not isinstance(value, str):
        raise DeveloperDataError("Symbol reference assets must be storage-relative string paths.")
    normalized = relativize_storage_path(value, allowed_roots=("symbols",), default_root="symbols")
    if PurePosixPath(normalized).parts[0] != "symbols":
        normalized = PurePosixPath("symbols", normalized).as_posix()
    return _validate_storage_asset_path(normalized, allowed_root="symbols")


def _card_record(card: Card) -> CardRecord:
    versions = sorted(card.versions.all(), key=lambda row: row.version_number)
    latest_number = card.latest_version.version_number if card.latest_version is not None else None
    return CardRecord(
        key=card.key,
        label=card.label,
        card_pool=cast(CardPool, card.card_pool),
        card_roles=list(card_role_keys(card)),
        card_factions=list(card_faction_keys(card)),
        card_mana_families=list(card_mana_family_keys(card)),
        deck_building_config=dict(card.deck_building_config_json),
        lifecycle_status=card.lifecycle_status,
        card_back_override_checksum=(
            card.card_back_override.checksum
            if card.card_back_override is not None
            else None
        ),
        latest_version_number=latest_number,
        aliases=[
            CardAliasRecord(key=alias.key, label=alias.label)
            for alias in sorted(card.aliases.all(), key=lambda row: row.key)
        ],
        versions=[_card_version_record(version) for version in versions],
    )


def _card_version_record(version: Any) -> CardVersionRecord:
    return CardVersionRecord(
        version_number=version.version_number,
        template_key=version.template.key,
        image_hash=version.image_hash,
        name=version.name,
        type_line=version.type_line,
        mana_cost=version.mana_cost,
        mana_symbols=list(version.mana_symbols_json),
        mana_value=version.mana_value,
        attack=version.attack,
        health=version.health,
        rules_text_raw=version.rules_text_raw,
        rules_text_enriched=version.rules_text_enriched,
        rules_text=version.rules_text,
        confidence=version.confidence,
        field_sources=dict(version.field_sources_json),
        parsed_snapshot=dict(version.parsed_snapshot_json),
        is_latest=version.is_latest,
        previous_version_number=(
            version.previous_version.version_number if version.previous_version_id else None
        ),
        content_version_number=(
            version.content_version.version_number if version.content_version_id else None
        ),
        keyword_keys=sorted(link.keyword.key for link in version.card_version_keywords.all()),
        tag_keys=sorted(link.tag.key for link in version.card_version_tags.all()),
        symbol_keys=sorted(link.symbol.key for link in version.card_version_symbols.all()),
        type_keys=sorted(link.type.key for link in version.card_version_types.all()),
        images=[
            CardImageRecord(
                stored_path=_validate_storage_asset_path(
                    relativize_image_storage_path(image.stored_path),
                    allowed_root="images",
                ),
                width=image.width,
                height=image.height,
                checksum=image.checksum,
            )
            for image in sorted(version.images.all(), key=lambda row: (row.created_at, row.id))
        ],
    )


def _group_record(group: CardGroup) -> CardGroupRecord:
    return CardGroupRecord(
        key=group.key,
        name=group.name,
        anchor_card_ref=_card_reference_record(group.anchor_card),
        members=[
            CardGroupMemberRecord(
                card_ref=_card_reference_record(member.card),
                position=member.position,
            )
            for member in sorted(group.members.all(), key=lambda row: row.position)
        ],
    )


def _card_reference_record(card: Card) -> CardReferenceRecord:
    return CardReferenceRecord(
        key=card.key,
        card_pool=cast(CardPool, card.card_pool),
        card_factions=list(card_faction_keys(card)),
        card_mana_families=list(card_mana_family_keys(card)),
    )


def _card_back_record(card_back: CardBack) -> CardBackRecord:
    return CardBackRecord(
        label=card_back.label,
        stored_path=_validate_storage_asset_path(
            relativize_image_storage_path(card_back.stored_path),
            allowed_root="images",
        ),
        width=card_back.width,
        height=card_back.height,
        checksum=card_back.checksum,
    )


def _optional_card_back_checksum(card_back: CardBack | None) -> str | None:
    return card_back.checksum if card_back is not None else None


def _validate_coverage(
    selection: DeveloperDataSelection,
    payload: DeveloperDataPayload,
) -> None:
    coverage = selection.coverage
    errors: list[str] = []
    if len(payload.cards) < coverage.min_cards:
        errors.append(f"requires at least {coverage.min_cards} cards")
    for card_pool, minimum in coverage.min_cards_by_pool.items():
        count = sum(card.card_pool == card_pool for card in payload.cards)
        if count < minimum:
            errors.append(f"requires at least {minimum} {card_pool} cards")
    for card_role, minimum in coverage.min_cards_by_role.items():
        count = sum(
            (not card.card_roles if card_role == "standard" else card_role in card.card_roles)
            for card in payload.cards
        )
        if count < minimum:
            errors.append(f"requires at least {minimum} cards with role {card_role}")
    if (
        sum(card.lifecycle_status == "deprecated" for card in payload.cards)
        < coverage.min_deprecated_cards
    ):
        errors.append(f"requires at least {coverage.min_deprecated_cards} deprecated cards")
    if len(payload.card_groups) < coverage.min_card_groups:
        errors.append(f"requires at least {coverage.min_card_groups} card groups")
    if (
        sum(len(card.versions) > 1 for card in payload.cards)
        < coverage.min_cards_with_multiple_versions
    ):
        errors.append(
            f"requires at least {coverage.min_cards_with_multiple_versions} cards with version history"
        )
    template_keys = {template.key for template in payload.templates}
    missing_templates = sorted(set(coverage.required_template_keys) - template_keys)
    if missing_templates:
        errors.append(f"missing required templates: {', '.join(missing_templates)}")
    tag_keys = {tag.key for tag in payload.tags}
    missing_tags = sorted(set(coverage.required_tag_keys) - tag_keys)
    if missing_tags:
        errors.append(f"missing required tags: {', '.join(missing_tags)}")
    faction_counts = {
        faction: sum(faction in card.card_factions for card in payload.cards)
        for faction in coverage.min_cards_by_faction
    }
    for faction, minimum in coverage.min_cards_by_faction.items():
        if faction_counts[faction] < minimum:
            errors.append(
                f"faction {faction} has {faction_counts[faction]} cards; requires {minimum}"
            )
    mana_family_counts = {
        family: sum(family in card.card_mana_families for card in payload.cards)
        for family in coverage.min_cards_by_mana_family
    }
    for family, minimum in coverage.min_cards_by_mana_family.items():
        if mana_family_counts[family] < minimum:
            errors.append(
                f"mana family {family} has {mana_family_counts[family]} cards; "
                f"requires {minimum}"
            )
    available_rules = {
        (
            rule.card_pool,
            rule.target_kind,
            rule.target_key,
            rule.source_kind,
            rule.source_key,
            rule.enabled,
        )
        for rule in payload.classification_rules
    }
    missing_rules = [
        rule
        for rule in coverage.required_classification_rules
        if (
            rule.card_pool,
            rule.target_kind,
            rule.target_key,
            rule.source_kind,
            rule.source_key,
            rule.enabled,
        )
        not in available_rules
    ]
    if missing_rules:
        errors.append(
            "missing required classification rules: "
            + ", ".join(
                f"{rule.card_pool}/{rule.target_kind}:{rule.target_key}"
                f"<-{rule.source_kind}:{rule.source_key}"
                for rule in missing_rules
            )
        )
    player_default = next(
        (
            row.card_back_checksum
            for row in payload.card_back_pool_defaults
            if row.card_pool == PLAYER_CARD_POOL
        ),
        None,
    )
    if player_default is None:
        errors.append("requires a Player pool default card back")
    if errors:
        raise DeveloperDataError("Developer-data coverage failed: " + "; ".join(errors))


_FORBIDDEN_DATA_KEYS = {
    "debug_crop",
    "debug_crop_path",
    "raw_ocr",
    "raw_ocr_json",
    "server_path",
    "source_file",
    "source_path",
    "upload_path",
}
_FORBIDDEN_CREDENTIAL_KEYS = {
    "api_key",
    "credential",
    "credentials",
    "password",
    "private_key",
    "secret",
    "token",
}
_FORBIDDEN_CREDENTIAL_KEY_SUFFIXES = tuple(f"_{key}" for key in _FORBIDDEN_CREDENTIAL_KEYS)
_ALLOWED_PUBLIC_CREDENTIAL_LIKE_KEYS = {"text_token"}
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _validate_payload_sanitization(payload: DeveloperDataPayload) -> None:
    _validate_public_json(payload.model_dump(mode="json"), context="developer-data payload")


def _validate_public_json(value: object, *, context: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = str(key).strip().lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_DATA_KEYS:
                raise DeveloperDataError(f"Forbidden private field in {context}: {key}")
            if _is_credential_key(normalized_key):
                raise DeveloperDataError(f"Forbidden credential field in {context}: {key}")
            _validate_public_json(nested, context=f"{context}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_public_json(nested, context=f"{context}[{index}]")
        return
    if isinstance(value, str) and (
        _WINDOWS_ABSOLUTE_PATH.match(value) or value.startswith(("/", "\\\\"))
    ):
        raise DeveloperDataError(f"Forbidden absolute filesystem path in {context}.")


def _is_credential_key(normalized_key: str) -> bool:
    if normalized_key in _ALLOWED_PUBLIC_CREDENTIAL_LIKE_KEYS:
        return False
    return normalized_key in _FORBIDDEN_CREDENTIAL_KEYS or normalized_key.endswith(
        _FORBIDDEN_CREDENTIAL_KEY_SUFFIXES
    )


def _copy_payload_assets(payload: DeveloperDataPayload, *, staging_root: Path) -> None:
    stored_paths = {
        image.stored_path
        for card in payload.cards
        for version in card.versions
        for image in version.images
    }
    stored_paths.update(asset for symbol in payload.symbols for asset in symbol.reference_assets)
    stored_paths.update(card_back.stored_path for card_back in payload.card_backs)
    for stored_path in sorted(stored_paths):
        source = _resolve_storage_asset(stored_path)
        destination = staging_root / "assets" / Path(stored_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _resolve_storage_asset(stored_path: str) -> Path:
    normalized = _validate_storage_asset_path(stored_path)
    storage_root = settings.storage_root_dir.resolve()
    target = (storage_root / Path(normalized)).resolve()
    try:
        target.relative_to(storage_root)
    except ValueError as exc:
        raise DeveloperDataError(f"Asset escapes the storage root: {stored_path}") from exc
    if not target.is_file():
        raise DeveloperDataError(f"Referenced developer-data asset is missing: {stored_path}")
    return target


def _validate_storage_asset_path(value: str, *, allowed_root: str | None = None) -> str:
    if not value or "\\" in value:
        raise DeveloperDataError(f"Unsafe storage-relative asset path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise DeveloperDataError(f"Unsafe storage-relative asset path: {value!r}")
    if path.parts[0] not in {"images", "symbols"}:
        raise DeveloperDataError(f"Unsupported developer-data asset root: {value}")
    if allowed_root is not None and path.parts[0] != allowed_root:
        raise DeveloperDataError(f"Expected a {allowed_root} asset path: {value}")
    return path.as_posix()


def _build_file_manifest(staging_root: Path) -> list[BundleFileRecord]:
    return [
        BundleFileRecord(
            path=path.relative_to(staging_root).as_posix(),
            sha256=calculate_checksum(path),
            size_bytes=path.stat().st_size,
        )
        for path in sorted(staging_root.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    ]


def _payload_counts(payload: DeveloperDataPayload) -> dict[str, int]:
    return {
        "keywords": len(payload.keywords),
        "tags": len(payload.tags),
        "types": len(payload.types),
        "symbols": len(payload.symbols),
        "templates": len(payload.templates),
        "classification_rules": len(payload.classification_rules),
        "deck_tags": len(payload.deck_tags),
        "content_versions": len(payload.content_versions),
        "cards": len(payload.cards),
        "card_versions": sum(len(card.versions) for card in payload.cards),
        "card_images": sum(
            len(version.images) for card in payload.cards for version in card.versions
        ),
        "card_groups": len(payload.card_groups),
        "card_backs": len(payload.card_backs),
    }


def _latest_core_migration() -> str:
    return (
        MigrationRecorder.Migration.objects.filter(app="card_reader_core")
        .order_by("-applied", "-name")
        .values_list("name", flat=True)
        .first()
        or "none"
    )


def _sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()

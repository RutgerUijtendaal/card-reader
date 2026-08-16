from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from django.db import transaction

from card_reader_core.database import retry_sqlite_write
from card_reader_core.models import (
    Card,
    CardAlias,
    CardClassificationInferenceEvidence,
    DEFAULT_CARD_POOL,
    EVIL_CARD_POOL,
    CardFaction,
    CardPool,
    CardRole,
    CardRoleAssignment,
    CardVersion,
    ImportJobItem,
    ImportJobStatus,
    ParseResult,
    card_faction_identity_key,
    card_faction_keys,
    card_mana_family_keys,
    card_is_deprecated,
    card_role_keys,
    now_utc,
)
from card_reader_core.metadata import ManaFamily
from card_reader_core.repositories.classification_reviews import (
    create_classification_review_item,
)
from card_reader_core.repositories.import_jobs import (
    CARD_CLASSIFICATION_CHANGED_WHILE_QUEUED_WARNING,
    EVIL_FACTION_UNRESOLVED_WARNING,
    MATCHED_DEPRECATED_CARD_WARNING,
    remove_import_warning,
    upsert_import_warning,
)

from ..helpers import extract_mana_symbols, infer_mana_value, normalize_slug_key, to_int_or_none
from ..metadata import (
    SuggestionCandidate,
    get_keywords_for_card_version,
    get_symbols_for_card_version,
    get_tags_for_card_version,
    get_types_for_card_version,
    replace_card_version_metadata_suggestions,
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
)
from ..templates import get_template_by_key
from .images import save_image_record
from .classification import set_card_mana_families
from .identity import change_card_identity, create_card_identity, resolve_card_by_name_key
from .queries import get_latest_card_version
from .snapshots import (
    DEFAULT_FIELD_SOURCES,
    FIELD_SOURCE_AUTO,
    build_parsed_snapshot,
    decode_field_sources,
)
from .types import ParsedCardSaveResult


UnknownEvilFactionMatchReason = Literal[
    "existing_unresolved_card",
    "matched_checksum",
    "matched_name",
    "matched_checksum_and_name",
    "no_candidate",
    "ambiguous_checksum",
    "ambiguous_name",
    "conflicting_evidence",
]


@dataclass(frozen=True)
class UnknownEvilFactionMatch:
    card: Card | None
    reason: UnknownEvilFactionMatchReason
    checksum_candidate_count: int
    name_candidate_count: int


def save_parsed_card(
    *,
    item: ImportJobItem,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    keyword_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    symbol_ids: list[str] | None = None,
    tag_suggestions: list[SuggestionCandidate] | None = None,
    type_suggestions: list[SuggestionCandidate] | None = None,
    reparse_existing: bool = True,
    card_pool: CardPool = DEFAULT_CARD_POOL,
    resolved_card_roles: tuple[CardRole, ...] = (),
    resolved_card_factions: tuple[CardFaction, ...] = (),
    resolved_card_mana_families: tuple[ManaFamily, ...] = (),
    classification_evidence: CardClassificationInferenceEvidence | None = None,
) -> CardVersion:
    return save_parsed_card_result(
        item=item,
        template_id=template_id,
        checksum=checksum,
        normalized_fields=normalized_fields,
        confidence=confidence,
        raw_ocr=raw_ocr,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
        tag_suggestions=tag_suggestions,
        type_suggestions=type_suggestions,
        reparse_existing=reparse_existing,
        card_pool=card_pool,
        resolved_card_roles=resolved_card_roles,
        resolved_card_factions=resolved_card_factions,
        resolved_card_mana_families=resolved_card_mana_families,
        classification_evidence=classification_evidence,
    ).version


@retry_sqlite_write
def save_parsed_card_result(
    *,
    item: ImportJobItem,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    keyword_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    symbol_ids: list[str] | None = None,
    tag_suggestions: list[SuggestionCandidate] | None = None,
    type_suggestions: list[SuggestionCandidate] | None = None,
    reparse_existing: bool = True,
    card_pool: CardPool = DEFAULT_CARD_POOL,
    resolved_card_roles: tuple[CardRole, ...] = (),
    resolved_card_factions: tuple[CardFaction, ...] = (),
    resolved_card_mana_families: tuple[ManaFamily, ...] = (),
    classification_evidence: CardClassificationInferenceEvidence | None = None,
) -> ParsedCardSaveResult:
    # A failed atomic attempt can leave relation assignments cached on the Python
    # instance even though the database transaction rolled them back. Every retry
    # must therefore start from the authoritative persisted item state.
    item = (
        ImportJobItem.objects.select_related(
            "job__content_version",
            "job__template",
            "target_card",
            "target_card_version__card",
        )
        .get(id=item.id)
    )
    resolved_evidence: CardClassificationInferenceEvidence = classification_evidence or {
        "roles": {
            "mode": "automatic",
            "matched_tag_sources": [],
            "matched_type_sources": [],
            "matched_symbol_sources": [],
            "matched_rules": [],
            "override_roles": [],
            "resolved_roles": list(resolved_card_roles),
            "snapshot_digest": "",
        },
        "factions": {
            "mode": "automatic",
            "matched_tag_sources": [],
            "matched_type_sources": [],
            "matched_symbol_sources": [],
            "matched_rules": [],
            "override_factions": [],
            "resolved_factions": list(resolved_card_factions),
            "snapshot_digest": "",
        },
        "mana_families": {
            "mode": "automatic",
            "matched_tag_sources": [],
            "matched_type_sources": [],
            "matched_symbol_sources": [],
            "matched_rules": [],
            "override_mana_families": [],
            "resolved_mana_families": list(resolved_card_mana_families),
            "snapshot_digest": "",
        },
    }
    parsed_name = normalized_fields.get("name", "").strip() or Path(item.source_file).stem
    is_unknown_evil_faction_import = (
        item.target_card_version is None
        and reparse_existing
        and card_pool == EVIL_CARD_POOL
        and not resolved_card_factions
    )
    with transaction.atomic():
        if item.target_card_version is not None:
            version = reparse_target_version(
                item=item,
                card_pool=card_pool,
                template_id=template_id,
                checksum=checksum,
                normalized_fields=normalized_fields,
                confidence=confidence,
                raw_ocr=raw_ocr,
                keyword_ids=keyword_ids or [],
                tag_ids=tag_ids or [],
                type_ids=type_ids or [],
                symbol_ids=symbol_ids or [],
                tag_suggestions=tag_suggestions or [],
                type_suggestions=type_suggestions or [],
            )
            finalize_import_item(
                item,
                version,
                card_pool=card_pool,
                resolved_card_roles=resolved_card_roles,
                resolved_card_factions=resolved_card_factions,
                resolved_card_mana_families=resolved_card_mana_families,
                evidence=resolved_evidence,
                is_new_card=False,
            )
            return ParsedCardSaveResult(version=version, created_new_version=False)

        existing_version = (
            _resolve_existing_import_version(
                checksum=checksum,
                card_pool=card_pool,
                resolved_card_factions=resolved_card_factions,
            )
            if reparse_existing
            else None
        )
        if existing_version is not None:
            if should_create_content_version_snapshot(item, existing_version):
                version = create_content_version_snapshot_from_existing(
                    item=item,
                    source_version=existing_version,
                    template_id=template_id,
                    checksum=checksum,
                    normalized_fields=normalized_fields,
                    confidence=confidence,
                    raw_ocr=raw_ocr,
                    keyword_ids=keyword_ids or [],
                    tag_ids=tag_ids or [],
                    type_ids=type_ids or [],
                    symbol_ids=symbol_ids or [],
                    tag_suggestions=tag_suggestions or [],
                    type_suggestions=type_suggestions or [],
                )
                apply_latest_version_identity(existing_version.card, version)
                created_new_version = True
            else:
                version = update_existing_version(
                    item,
                    existing_version,
                    normalized_fields,
                    confidence,
                    raw_ocr,
                    keyword_ids=keyword_ids or [],
                    tag_ids=tag_ids or [],
                    type_ids=type_ids or [],
                    symbol_ids=symbol_ids or [],
                    tag_suggestions=tag_suggestions or [],
                    type_suggestions=type_suggestions or [],
                )
                created_new_version = False
            finalize_import_item(
                item,
                version,
                card_pool=card_pool,
                resolved_card_roles=resolved_card_roles,
                resolved_card_factions=resolved_card_factions,
                resolved_card_mana_families=resolved_card_mana_families,
                evidence=resolved_evidence,
                is_new_card=False,
                unknown_evil_faction_match=(
                    UnknownEvilFactionMatch(
                        card=existing_version.card,
                        reason="existing_unresolved_card",
                        checksum_candidate_count=0,
                        name_candidate_count=0,
                    )
                    if is_unknown_evil_faction_import
                    else None
                ),
            )
            return ParsedCardSaveResult(
                version=version,
                created_new_version=created_new_version,
            )

        existing_unknown_faction_card = (
            resolve_card_by_name_key(
                name=parsed_name,
                card_pool=card_pool,
                card_factions=resolved_card_factions,
            )
            if is_unknown_evil_faction_import
            else None
        )
        unknown_evil_faction_match = (
            UnknownEvilFactionMatch(
                card=existing_unknown_faction_card,
                reason="existing_unresolved_card",
                checksum_candidate_count=0,
                name_candidate_count=0,
            )
            if existing_unknown_faction_card is not None
            else (
                _resolve_unknown_evil_faction_import(
                    checksum=checksum,
                    parsed_name=parsed_name,
                )
                if is_unknown_evil_faction_import
                else None
            )
        )
        matched_card = (
            unknown_evil_faction_match.card
            if unknown_evil_faction_match is not None
            else None
        )
        if matched_card is None:
            card, created_new_card = create_card_identity(
                name=parsed_name,
                card_pool=card_pool,
                card_factions=resolved_card_factions,
            )
        else:
            card = matched_card
            created_new_card = False
        if created_new_card:
            CardRoleAssignment.objects.bulk_create(
                [CardRoleAssignment(card=card, role=role) for role in resolved_card_roles]
            )
            set_card_mana_families(
                card=card,
                mana_families=resolved_card_mana_families,
            )

        latest = get_latest_card_version(card.id)
        if latest and latest.image_hash == checksum and reparse_existing:
            if should_create_content_version_snapshot(item, latest):
                version = create_content_version_snapshot_from_existing(
                    item=item,
                    source_version=latest,
                    template_id=template_id,
                    checksum=checksum,
                    normalized_fields=normalized_fields,
                    confidence=confidence,
                    raw_ocr=raw_ocr,
                    keyword_ids=keyword_ids or [],
                    tag_ids=tag_ids or [],
                    type_ids=type_ids or [],
                    symbol_ids=symbol_ids or [],
                    tag_suggestions=tag_suggestions or [],
                    type_suggestions=type_suggestions or [],
                )
                apply_latest_version_identity(card, version)
                created_new_version = True
            else:
                version = update_existing_version(
                    item,
                    latest,
                    normalized_fields,
                    confidence,
                    raw_ocr,
                    keyword_ids=keyword_ids or [],
                    tag_ids=tag_ids or [],
                    type_ids=type_ids or [],
                    symbol_ids=symbol_ids or [],
                    tag_suggestions=tag_suggestions or [],
                    type_suggestions=type_suggestions or [],
                )
                created_new_version = False
            finalize_import_item(
                item,
                version,
                card_pool=card_pool,
                resolved_card_roles=resolved_card_roles,
                resolved_card_factions=resolved_card_factions,
                resolved_card_mana_families=resolved_card_mana_families,
                evidence=resolved_evidence,
                is_new_card=created_new_card,
                unknown_evil_faction_match=unknown_evil_faction_match,
            )
            return ParsedCardSaveResult(
                version=version,
                created_new_version=created_new_version,
            )

        version = create_parsed_card_version(
            item=item,
            card=card,
            template_id=template_id,
            checksum=checksum,
            normalized_fields=normalized_fields,
            confidence=confidence,
            raw_ocr=raw_ocr,
            keyword_ids=keyword_ids or [],
            tag_ids=tag_ids or [],
            type_ids=type_ids or [],
            symbol_ids=symbol_ids or [],
            tag_suggestions=tag_suggestions or [],
            type_suggestions=type_suggestions or [],
        )
        apply_latest_version_identity(card, version)
        finalize_import_item(
            item,
            version,
            card_pool=card_pool,
            resolved_card_roles=resolved_card_roles,
            resolved_card_factions=resolved_card_factions,
            resolved_card_mana_families=resolved_card_mana_families,
            evidence=resolved_evidence,
            is_new_card=created_new_card,
            unknown_evil_faction_match=unknown_evil_faction_match,
        )
        return ParsedCardSaveResult(version=version, created_new_version=True)


def _resolve_existing_import_version(
    *,
    checksum: str,
    card_pool: CardPool,
    resolved_card_factions: tuple[CardFaction, ...],
) -> CardVersion | None:
    faction_key = card_faction_identity_key(resolved_card_factions)
    return (
        CardVersion.objects.filter(
            image_hash=checksum,
            is_latest=True,
            card__card_pool=card_pool,
            card__faction_identity_key=faction_key,
        )
        .order_by("-updated_at")
        .first()
    )


def _resolve_unknown_evil_faction_import(
    *,
    checksum: str,
    parsed_name: str,
) -> UnknownEvilFactionMatch:
    """Resolve an unclassified Evil import only when its evidence is unambiguous."""
    empty_faction_key = card_faction_identity_key(())
    checksum_candidates = (
        CardVersion.objects.filter(
            image_hash=checksum,
            card__card_pool=EVIL_CARD_POOL,
        )
        .exclude(card__faction_identity_key=empty_faction_key)
        .order_by()
        .values_list("card_id", flat=True)
        .distinct()
    )
    checksum_candidate_count = checksum_candidates.count()
    checksum_card_id = checksum_candidates.first() if checksum_candidate_count == 1 else None

    name_key = normalize_slug_key(parsed_name)
    name_card_ids: set[str] = set()
    if name_key:
        name_card_ids.update(
            Card.objects.filter(card_pool=EVIL_CARD_POOL, key=name_key)
            .exclude(faction_identity_key=empty_faction_key)
            .values_list("id", flat=True)
        )
        name_card_ids.update(
            CardAlias.objects.filter(card_pool=EVIL_CARD_POOL, key=name_key)
            .exclude(faction_identity_key=empty_faction_key)
            .values_list("card_id", flat=True)
        )
    name_candidate_count = len(name_card_ids)
    name_card_id = next(iter(name_card_ids)) if name_candidate_count == 1 else None

    if checksum_candidate_count > 1:
        reason: UnknownEvilFactionMatchReason = "ambiguous_checksum"
        matched_card_id = None
    elif name_candidate_count > 1:
        reason = "ambiguous_name"
        matched_card_id = None
    elif (
        checksum_card_id is not None
        and name_card_id is not None
        and checksum_card_id != name_card_id
    ):
        reason = "conflicting_evidence"
        matched_card_id = None
    elif checksum_card_id is not None:
        reason = (
            "matched_checksum_and_name"
            if name_card_id == checksum_card_id
            else "matched_checksum"
        )
        matched_card_id = checksum_card_id
    elif name_card_id is not None:
        reason = "matched_name"
        matched_card_id = name_card_id
    else:
        reason = "no_candidate"
        matched_card_id = None

    matched_card = (
        Card.objects.filter(
            id=matched_card_id,
            card_pool=EVIL_CARD_POOL,
        )
        .exclude(faction_identity_key=empty_faction_key)
        .first()
        if matched_card_id is not None
        else None
    )
    if matched_card_id is not None and matched_card is None:
        reason = "no_candidate"

    return UnknownEvilFactionMatch(
        card=matched_card,
        reason=reason,
        checksum_candidate_count=checksum_candidate_count,
        name_candidate_count=name_candidate_count,
    )


def apply_latest_version_identity(card: Card, version: CardVersion) -> None:
    if normalize_slug_key(version.name) != card.key or card.label != version.name:
        change_card_identity(card=card, label=version.name)
    card.latest_version = version
    card.updated_at = now_utc()
    card.save(update_fields=["latest_version", "updated_at"])


def should_create_content_version_snapshot(item: ImportJobItem, version: CardVersion) -> bool:
    job_content_version = item.job.content_version
    return job_content_version is not None and version.content_version != job_content_version


def create_parsed_card_version(
    *,
    item: ImportJobItem,
    card: Card,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
    tag_suggestions: list[SuggestionCandidate],
    type_suggestions: list[SuggestionCandidate],
) -> CardVersion:
    version = create_new_version(item, card, template_id, checksum, normalized_fields, confidence)
    replace_card_version_keywords(card_version_id=version.id, keyword_ids=keyword_ids)
    replace_card_version_tags(card_version_id=version.id, tag_ids=tag_ids)
    replace_card_version_types(card_version_id=version.id, type_ids=type_ids)
    replace_card_version_symbols(
        card_version_id=version.id,
        symbol_ids=symbol_ids,
    )
    parse_result = save_parse_result(version, raw_ocr, normalized_fields, confidence)
    replace_card_version_metadata_suggestions(
        card_version_id=version.id,
        kind="tag",
        candidates=tag_suggestions,
        parse_result_id=parse_result.id,
    )
    replace_card_version_metadata_suggestions(
        card_version_id=version.id,
        kind="type",
        candidates=type_suggestions,
        parse_result_id=parse_result.id,
    )
    save_parsed_snapshot(
        version,
        normalized_fields=normalized_fields,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
    )
    save_image_record(version, item.source_file, checksum)
    return version


def create_content_version_snapshot_from_existing(
    *,
    item: ImportJobItem,
    source_version: CardVersion,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
    tag_suggestions: list[SuggestionCandidate],
    type_suggestions: list[SuggestionCandidate],
) -> CardVersion:
    version = clone_card_version_for_content_version_snapshot(
        item=item,
        source_version=source_version,
        template_id=template_id,
        checksum=checksum,
    )
    apply_parsed_output_to_version(
        version,
        normalized_fields=normalized_fields,
        confidence=confidence,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
    )
    parse_result = save_parse_result(version, raw_ocr, normalized_fields, confidence)
    replace_card_version_metadata_suggestions(
        card_version_id=version.id,
        kind="tag",
        candidates=tag_suggestions,
        parse_result_id=parse_result.id,
    )
    replace_card_version_metadata_suggestions(
        card_version_id=version.id,
        kind="type",
        candidates=type_suggestions,
        parse_result_id=parse_result.id,
    )
    save_parsed_snapshot(
        version,
        normalized_fields=normalized_fields,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
    )
    version.updated_at = now_utc()
    version.save()
    save_image_record(version, item.source_file, checksum)
    return version


def clone_card_version_for_content_version_snapshot(
    *,
    item: ImportJobItem,
    source_version: CardVersion,
    template_id: str,
    checksum: str,
) -> CardVersion:
    template = get_template_by_key(key=template_id)
    if template is None:
        raise ValueError(f"Unknown template_id '{template_id}'")

    source_version.is_latest = False
    source_version.updated_at = now_utc()
    source_version.save(update_fields=["is_latest", "updated_at"])
    version = CardVersion.objects.create(
        card=source_version.card,
        version_number=source_version.version_number + 1,
        template=template,
        image_hash=checksum,
        name=source_version.name,
        type_line=source_version.type_line,
        mana_cost=source_version.mana_cost,
        mana_symbols_json=source_version.mana_symbols_json,
        mana_value=source_version.mana_value,
        attack=source_version.attack,
        health=source_version.health,
        rules_text_raw=source_version.rules_text_raw,
        rules_text_enriched=source_version.rules_text_enriched,
        rules_text=source_version.rules_text,
        confidence=source_version.confidence,
        field_sources_json=source_version.field_sources_json,
        parsed_snapshot_json=source_version.parsed_snapshot_json,
        is_latest=True,
        previous_version=source_version,
        content_version=item.job.content_version,
    )
    replace_card_version_keywords(
        card_version_id=version.id,
        keyword_ids=[row.id for row in get_keywords_for_card_version(source_version.id)],
    )
    replace_card_version_tags(
        card_version_id=version.id,
        tag_ids=[row.id for row in get_tags_for_card_version(source_version.id)],
    )
    replace_card_version_types(
        card_version_id=version.id,
        type_ids=[row.id for row in get_types_for_card_version(source_version.id)],
    )
    replace_card_version_symbols(
        card_version_id=version.id,
        symbol_ids=[row.id for row in get_symbols_for_card_version(source_version.id)],
    )
    return version


def reparse_target_version(
    *,
    item: ImportJobItem,
    card_pool: CardPool,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
    tag_suggestions: list[SuggestionCandidate],
    type_suggestions: list[SuggestionCandidate],
) -> CardVersion:
    target_version = item.target_card_version
    if target_version is None:
        raise ValueError("Target card version is required for targeted reparses")
    requested_card = item.target_card
    with transaction.atomic():
        version = (
            CardVersion.objects.select_for_update()
            .select_related("card", "template", "previous_version")
            .filter(id=target_version.id)
            .first()
        )
        if version is None:
            raise ValueError(f"Target card version '{target_version.id}' does not exist")
        if not version.is_latest:
            raise ValueError("Only latest card versions can be reparsed")
        if requested_card is not None and version.card.id != requested_card.id:
            raise ValueError("Target card version does not belong to the requested card")

        target_card = (
            Card.objects.select_for_update().filter(id=version.card.id).first()
        )
        if target_card is None:
            raise ValueError("The target Card no longer exists; queue a new reparse.")
        if target_card.card_pool != card_pool:
            raise ValueError(
                "The target Card pool changed while this reparse was queued; "
                "queue a new reparse for its current pool."
            )
        version.card = target_card
        reset_manual_state = version.template.key != template_id
        return update_existing_version(
            item,
            version,
            normalized_fields,
            confidence,
            raw_ocr,
            keyword_ids=keyword_ids,
            tag_ids=tag_ids,
            type_ids=type_ids,
            symbol_ids=symbol_ids,
            tag_suggestions=tag_suggestions,
            type_suggestions=type_suggestions,
            template_id=template_id,
            reset_manual_state=reset_manual_state,
        )


def apply_parsed_fields_to_version(
    version: CardVersion,
    *,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> None:
    version.name = normalized_fields.get("name", "")
    version.type_line = normalized_fields.get("type_line", "")
    version.mana_cost = normalized_fields.get("mana_cost", "")
    version.mana_symbols_json = extract_mana_symbols(normalized_fields)
    version.mana_value = infer_mana_value(
        mana_cost=version.mana_cost,
        mana_symbols=version.mana_symbols_json,
        mana_total=normalized_fields.get("mana_total"),
    )
    version.attack = to_int_or_none(normalized_fields.get("attack"))
    version.health = to_int_or_none(normalized_fields.get("health"))
    version.rules_text_raw = normalized_fields.get("rules_text_raw", "")
    version.rules_text_enriched = normalized_fields.get("rules_text_enriched", "")
    version.rules_text = normalized_fields.get("rules_text", "")
    version.confidence = float(confidence.get("overall", 0.0))


def update_existing_version(
    item: ImportJobItem,
    version: CardVersion,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    *,
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
    tag_suggestions: list[SuggestionCandidate],
    type_suggestions: list[SuggestionCandidate],
    template_id: str | None = None,
    reset_manual_state: bool = False,
) -> CardVersion:
    if template_id is not None:
        template = get_template_by_key(key=template_id)
        if template is None:
            raise ValueError(f"Unknown template_id '{template_id}'")
        version.template = template
    if reset_manual_state:
        version.field_sources_json = DEFAULT_FIELD_SOURCES
    apply_parsed_output_to_version(
        version,
        normalized_fields=normalized_fields,
        confidence=confidence,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
    )
    parse_result = save_parse_result(version, raw_ocr, normalized_fields, confidence)
    replace_card_version_metadata_suggestions(
        card_version_id=version.id,
        kind="tag",
        candidates=tag_suggestions,
        parse_result_id=parse_result.id,
    )
    replace_card_version_metadata_suggestions(
        card_version_id=version.id,
        kind="type",
        candidates=type_suggestions,
        parse_result_id=parse_result.id,
    )
    save_parsed_snapshot(
        version,
        normalized_fields=normalized_fields,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
    )
    version.updated_at = now_utc()
    version.save()
    card = Card.objects.filter(id=version.card.id).first()
    if card is not None:
        apply_latest_version_identity(card, version)
    return version


def sync_import_item_lifecycle_warning(item: ImportJobItem, card: Card) -> None:
    if not card_is_deprecated(card):
        remove_import_warning(item, MATCHED_DEPRECATED_CARD_WARNING)
        return

    upsert_import_warning(
        item,
        {
            "code": MATCHED_DEPRECATED_CARD_WARNING,
            "message": f"Import matched deprecated card '{card.label}'. The card remains deprecated.",
        },
    )


def sync_unknown_evil_faction_warning(
    item: ImportJobItem,
    card: Card,
    match: UnknownEvilFactionMatch | None,
) -> None:
    if match is None or card_faction_keys(card):
        remove_import_warning(item, EVIL_FACTION_UNRESOLVED_WARNING)
        return

    ambiguous_reasons = {
        "ambiguous_checksum",
        "ambiguous_name",
        "conflicting_evidence",
    }
    message = (
        "No Evil faction was inferred and existing Card evidence was ambiguous. "
        "No automatic merge was performed; review and assign this Card's faction."
        if match.reason in ambiguous_reasons
        else "No Evil faction was inferred. Review and assign this Card's faction."
    )
    upsert_import_warning(
        item,
        {
            "code": EVIL_FACTION_UNRESOLVED_WARNING,
            "message": message,
            "details": {
                "reason": match.reason,
                "checksum_candidate_count": match.checksum_candidate_count,
                "name_candidate_count": match.name_candidate_count,
            },
        },
    )


def finalize_import_item(
    item: ImportJobItem,
    version: CardVersion,
    *,
    card_pool: CardPool,
    resolved_card_roles: tuple[CardRole, ...],
    resolved_card_factions: tuple[CardFaction, ...],
    resolved_card_mana_families: tuple[ManaFamily, ...],
    evidence: CardClassificationInferenceEvidence,
    is_new_card: bool,
    unknown_evil_faction_match: UnknownEvilFactionMatch | None = None,
) -> None:
    card = version.card
    live_roles = card_role_keys(card)
    live_factions = card_faction_keys(card)
    live_mana_families = card_mana_family_keys(card)
    evidence_payload: dict[str, object] = dict(evidence)
    evidence_payload["live_classification"] = {
        "card_pool": card.card_pool,
        "card_roles": list(live_roles),
        "card_factions": list(live_factions),
        "card_mana_families": list(live_mana_families),
    }

    if item.target_card_pool_snapshot is not None:
        queued_roles = tuple(item.target_card_roles_snapshot_json)
        queued_factions = tuple(item.target_card_factions_snapshot_json)
        queued_mana_families = tuple(item.target_card_mana_families_snapshot_json)
        evidence_payload["queued_target_classification"] = {
            "card_pool": item.target_card_pool_snapshot,
            "card_roles": list(queued_roles),
            "card_factions": list(queued_factions),
            "card_mana_families": list(queued_mana_families),
        }
        if (
            item.target_card_pool_snapshot != card.card_pool
            or queued_roles != live_roles
            or queued_factions != live_factions
            or queued_mana_families != live_mana_families
        ):
            upsert_import_warning(
                item,
                {
                    "code": CARD_CLASSIFICATION_CHANGED_WHILE_QUEUED_WARNING,
                    "message": "Card classification changed while this reparse was queued; the live value was preserved.",
                    "details": {
                        "queued": evidence_payload["queued_target_classification"],
                        "live": evidence_payload["live_classification"],
                    },
                },
            )
        else:
            remove_import_warning(item, CARD_CLASSIFICATION_CHANGED_WHILE_QUEUED_WARNING)

    classification_mismatch = not is_new_card and (
        card.card_pool != card_pool
        or live_roles != resolved_card_roles
        or live_factions != resolved_card_factions
        or live_mana_families != resolved_card_mana_families
    )
    if classification_mismatch:
        existing_classification: dict[str, object] = {
            "card_pool": card.card_pool,
            "card_roles": list(live_roles),
            "card_factions": list(live_factions),
            "card_mana_families": list(live_mana_families),
        }
        inferred_classification: dict[str, object] = {
            "card_pool": card_pool,
            "card_roles": list(resolved_card_roles),
            "card_factions": list(resolved_card_factions),
            "card_mana_families": list(resolved_card_mana_families),
        }
        create_classification_review_item(
            import_item=item,
            card=card,
            card_version=version,
            existing_classification=existing_classification,
            inferred_classification=inferred_classification,
            inference_evidence=evidence_payload,
        )

    item.resolved_card_roles_json = list(resolved_card_roles)
    item.resolved_card_factions_json = list(resolved_card_factions)
    item.resolved_card_mana_families_json = list(resolved_card_mana_families)
    item.classification_inference_json = evidence_payload
    item.target_card = card
    item.target_card_version = version
    sync_unknown_evil_faction_warning(item, card, unknown_evil_faction_match)
    sync_import_item_lifecycle_warning(item, card)
    mark_item_completed(item)


def create_new_version(
    item: ImportJobItem,
    card: Card,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> CardVersion:
    template = get_template_by_key(key=template_id)
    if template is None:
        raise ValueError(f"Unknown template_id '{template_id}'")

    latest = get_latest_card_version(card.id)
    previous_version_id = None
    version_number = 1
    if latest is not None:
        latest.is_latest = False
        latest.updated_at = now_utc()
        latest.save(update_fields=["is_latest", "updated_at"])
        previous_version_id = latest.id
        version_number = latest.version_number + 1

    return CardVersion.objects.create(
        card=card,
        version_number=version_number,
        template=template,
        image_hash=checksum,
        name=normalized_fields.get("name", "").strip() or Path(item.source_file).stem,
        type_line=normalized_fields.get("type_line", ""),
        mana_cost=normalized_fields.get("mana_cost", ""),
        mana_symbols_json=extract_mana_symbols(normalized_fields),
        mana_value=infer_mana_value(
            mana_cost=normalized_fields.get("mana_cost", ""),
            mana_symbols=extract_mana_symbols(normalized_fields),
            mana_total=normalized_fields.get("mana_total"),
        ),
        attack=to_int_or_none(normalized_fields.get("attack")),
        health=to_int_or_none(normalized_fields.get("health")),
        rules_text_raw=normalized_fields.get("rules_text_raw", ""),
        rules_text_enriched=normalized_fields.get("rules_text_enriched", ""),
        rules_text=normalized_fields.get("rules_text", ""),
        confidence=float(confidence.get("overall", 0.0)),
        field_sources_json=DEFAULT_FIELD_SOURCES,
        parsed_snapshot_json=build_parsed_snapshot(normalized_fields, [], [], [], []),
        is_latest=True,
        previous_version_id=previous_version_id,
        content_version=item.job.content_version,
    )


def save_parse_result(
    version: CardVersion,
    raw_ocr: dict[str, object],
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> ParseResult:
    parse_result = ParseResult.objects.create(
        card_version=version,
        raw_ocr_json=raw_ocr,
        normalized_fields_json=normalized_fields,
        confidence_json=confidence,
    )
    version.parse_result = parse_result
    version.save(update_fields=["parse_result"])
    return parse_result


def save_parsed_snapshot(
    version: CardVersion,
    *,
    normalized_fields: dict[str, str],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
) -> None:
    version.parsed_snapshot_json = build_parsed_snapshot(
        normalized_fields,
        keyword_ids,
        tag_ids,
        type_ids,
        symbol_ids,
    )
    version.save(update_fields=["parsed_snapshot_json"])


def mark_item_completed(item: ImportJobItem) -> None:
    item.status = ImportJobStatus.completed
    item.error_message = None
    item.updated_at = now_utc()
    item.save(
        update_fields=[
            "status",
            "error_message",
            "warning_code",
            "warning_message",
            "warnings_json",
            "resolved_card_roles_json",
            "resolved_card_factions_json",
            "resolved_card_mana_families_json",
            "classification_inference_json",
            "target_card",
            "target_card_version",
            "updated_at",
        ]
    )


def apply_parsed_output_to_version(
    version: CardVersion,
    *,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
) -> None:
    field_sources = decode_field_sources(version.field_sources_json)
    if field_sources["fields"]["name"] == FIELD_SOURCE_AUTO:
        version.name = normalized_fields.get("name", "")
    if field_sources["fields"]["type_line"] == FIELD_SOURCE_AUTO:
        version.type_line = normalized_fields.get("type_line", "")
    if field_sources["fields"]["mana_cost"] == FIELD_SOURCE_AUTO:
        version.mana_cost = normalized_fields.get("mana_cost", "")
        version.mana_symbols_json = extract_mana_symbols(normalized_fields)
        version.mana_value = infer_mana_value(
            mana_cost=version.mana_cost,
            mana_symbols=version.mana_symbols_json,
            mana_total=normalized_fields.get("mana_total"),
        )
    if field_sources["fields"]["attack"] == FIELD_SOURCE_AUTO:
        version.attack = to_int_or_none(normalized_fields.get("attack"))
    if field_sources["fields"]["health"] == FIELD_SOURCE_AUTO:
        version.health = to_int_or_none(normalized_fields.get("health"))
    if field_sources["fields"]["rules_text"] == FIELD_SOURCE_AUTO:
        version.rules_text_enriched = normalized_fields.get("rules_text_enriched", "")
        version.rules_text = normalized_fields.get("rules_text", "")
    version.rules_text_raw = normalized_fields.get("rules_text_raw", "")
    if field_sources["fields"]["rules_text"] == FIELD_SOURCE_AUTO:
        version.rules_text_enriched = normalized_fields.get("rules_text_enriched", "")

    if field_sources["metadata"]["keywords"] == FIELD_SOURCE_AUTO:
        replace_card_version_keywords(card_version_id=version.id, keyword_ids=keyword_ids)
    if field_sources["metadata"]["tags"] == FIELD_SOURCE_AUTO:
        replace_card_version_tags(card_version_id=version.id, tag_ids=tag_ids)
    if field_sources["metadata"]["types"] == FIELD_SOURCE_AUTO:
        replace_card_version_types(card_version_id=version.id, type_ids=type_ids)
    if field_sources["metadata"]["symbols"] == FIELD_SOURCE_AUTO:
        replace_card_version_symbols(
            card_version_id=version.id,
            symbol_ids=symbol_ids,
        )

    version.confidence = float(confidence.get("overall", 0.0))

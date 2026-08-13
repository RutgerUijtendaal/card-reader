from __future__ import annotations

from pathlib import Path

from django.db import transaction

from card_reader_core.models import (
    Card,
    CardClassificationInferenceEvidence,
    DEFAULT_CARD_POOL,
    CardFaction,
    CardPool,
    CardRole,
    CardRoleAssignment,
    CardVersion,
    ImportJobItem,
    ImportJobStatus,
    LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION,
    ParseResult,
    card_faction_identity_key,
    card_faction_keys,
    card_is_deprecated,
    card_role_keys,
    now_utc,
)
from card_reader_core.repositories.import_jobs import (
    CARD_CLASSIFICATION_CHANGED_WHILE_QUEUED_WARNING,
    CARD_CLASSIFICATION_MISMATCH_WARNING,
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
from .identity import change_card_identity, create_card_identity
from .queries import get_latest_card_version
from .snapshots import (
    DEFAULT_FIELD_SOURCES,
    FIELD_SOURCE_AUTO,
    build_parsed_snapshot,
    decode_field_sources,
)
from .types import ParsedCardSaveResult


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
        classification_evidence=classification_evidence,
    ).version


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
    classification_evidence: CardClassificationInferenceEvidence | None = None,
) -> ParsedCardSaveResult:
    resolved_evidence: CardClassificationInferenceEvidence = classification_evidence or {
        "roles": {
            "mode": "automatic",
            "policy_version": LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION,
            "template_roles": [],
            "matched_tag_keys": [],
            "tag_roles": [],
            "override_roles": [],
            "resolved_roles": list(resolved_card_roles),
        },
        "factions": {
            "mode": "automatic",
            "policy_version": LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION,
            "template_factions": [],
            "matched_tag_keys": [],
            "tag_factions": [],
            "override_factions": [],
            "resolved_factions": list(resolved_card_factions),
        },
    }
    parsed_name = normalized_fields.get("name", "").strip() or Path(item.source_file).stem
    with transaction.atomic():
        if item.target_card_version is not None:
            version = reparse_target_version(
                item=item,
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
                evidence=resolved_evidence,
                is_new_card=False,
            )
            return ParsedCardSaveResult(version=version, created_new_version=False)

        existing_version = None
        if reparse_existing:
            existing_version = (
                CardVersion.objects.filter(
                    image_hash=checksum,
                    is_latest=True,
                    card__card_pool=card_pool,
                    card__faction_identity_key=card_faction_identity_key(
                        resolved_card_factions
                    ),
                )
                .order_by("-updated_at")
                .first()
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
                evidence=resolved_evidence,
                is_new_card=False,
            )
            return ParsedCardSaveResult(
                version=version,
                created_new_version=created_new_version,
            )

        card, created_new_card = create_card_identity(
            name=parsed_name,
            card_pool=card_pool,
            card_factions=resolved_card_factions,
        )
        if created_new_card:
            CardRoleAssignment.objects.bulk_create(
                [CardRoleAssignment(card=card, role=role) for role in resolved_card_roles]
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
                evidence=resolved_evidence,
                is_new_card=created_new_card,
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
            evidence=resolved_evidence,
            is_new_card=created_new_card,
        )
        return ParsedCardSaveResult(version=version, created_new_version=True)


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
    replace_card_version_symbols(card_version_id=version.id, symbol_ids=symbol_ids)
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
    version = (
        CardVersion.objects.select_related("card", "template", "previous_version")
        .filter(id=target_version.id)
        .first()
    )
    if version is None:
        raise ValueError(f"Target card version '{target_version.id}' does not exist")
    if not version.is_latest:
        raise ValueError("Only latest card versions can be reparsed")
    if item.target_card is not None and version.card.id != item.target_card.id:
        raise ValueError("Target card version does not belong to the requested card")

    reset_manual_state = version.template.key != template_id
    with transaction.atomic():
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


def finalize_import_item(
    item: ImportJobItem,
    version: CardVersion,
    *,
    card_pool: CardPool,
    resolved_card_roles: tuple[CardRole, ...],
    resolved_card_factions: tuple[CardFaction, ...],
    evidence: CardClassificationInferenceEvidence,
    is_new_card: bool,
) -> None:
    card = version.card
    live_roles = card_role_keys(card)
    live_factions = card_faction_keys(card)
    evidence_payload: dict[str, object] = dict(evidence)
    evidence_payload["live_classification"] = {
        "card_pool": card.card_pool,
        "card_roles": list(live_roles),
        "card_factions": list(live_factions),
    }

    if item.target_card_pool_snapshot is not None:
        queued_roles = tuple(item.target_card_roles_snapshot_json)
        queued_factions = tuple(item.target_card_factions_snapshot_json)
        evidence_payload["queued_target_classification"] = {
            "card_pool": item.target_card_pool_snapshot,
            "card_roles": list(queued_roles),
            "card_factions": list(queued_factions),
        }
        if (
            item.target_card_pool_snapshot != card.card_pool
            or queued_roles != live_roles
            or queued_factions != live_factions
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

    if is_new_card or (
        card.card_pool == card_pool
        and live_roles == resolved_card_roles
        and live_factions == resolved_card_factions
    ):
        remove_import_warning(item, CARD_CLASSIFICATION_MISMATCH_WARNING)
    else:
        upsert_import_warning(
            item,
            {
                "code": CARD_CLASSIFICATION_MISMATCH_WARNING,
                "message": "Inferred classification differs from the existing card; the existing classification was preserved.",
                "details": {
                    "inferred": {
                        "card_pool": card_pool,
                        "card_roles": list(resolved_card_roles),
                        "card_factions": list(resolved_card_factions),
                    },
                    "existing": evidence_payload["live_classification"],
                },
            },
        )

    item.resolved_card_roles_json = list(resolved_card_roles)
    item.resolved_card_factions_json = list(resolved_card_factions)
    item.classification_inference_json = evidence_payload
    item.target_card = card
    item.target_card_version = version
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
        replace_card_version_symbols(card_version_id=version.id, symbol_ids=symbol_ids)

    version.confidence = float(confidence.get("overall", 0.0))

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from django.db.models import Count, Q

from card_reader_core.models import (
    CardVersion,
    CardVersionMetadataSuggestion,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Keyword,
    MetadataSuggestion,
    Symbol,
    Tag,
    Type,
    now_utc,
)
from card_reader_core.rule_text import render_enriched_rule_text, replace_symbol_placeholder_key

MetadataModel = Keyword | Tag | Symbol | Type
MetadataRow = TypeVar("MetadataRow", bound=MetadataModel)


@dataclass(frozen=True)
class SuggestionCandidate:
    display_value: str
    normalized_value: str
    source_text: str
    normalized_source_text: str


@dataclass(frozen=True)
class MetadataSuggestionListRow:
    suggestion: MetadataSuggestion
    occurrence_count: int


def _list(model: Any, *, keys: set[str] | None = None) -> list[Any]:
    if keys is not None and not keys:
        return []
    query = model.objects.order_by("label")
    if keys is not None:
        query = query.filter(key__in=keys)
    return list(query)


def list_keywords(*, keys: set[str] | None = None) -> list[Keyword]:
    return _list(Keyword, keys=keys)


def list_tags(*, keys: set[str] | None = None) -> list[Tag]:
    return _list(Tag, keys=keys)


def list_symbols(*, keys: set[str] | None = None) -> list[Symbol]:
    return _list(Symbol, keys=keys)


def list_detectable_symbols() -> list[Symbol]:
    return list(Symbol.objects.filter(enabled=True, detector_type="template").order_by("label"))


def list_types(*, keys: set[str] | None = None) -> list[Type]:
    return _list(Type, keys=keys)


def get_keyword(entry_id: str) -> Keyword | None:
    return Keyword.objects.filter(id=entry_id).first()


def get_tag(entry_id: str) -> Tag | None:
    return Tag.objects.filter(id=entry_id).first()


def get_symbol(entry_id: str) -> Symbol | None:
    return Symbol.objects.filter(id=entry_id).first()


def get_type(entry_id: str) -> Type | None:
    return Type.objects.filter(id=entry_id).first()


def get_metadata_suggestion(entry_id: str) -> MetadataSuggestion | None:
    return (
        MetadataSuggestion.objects.filter(id=entry_id)
        .select_related("accepted_tag", "accepted_type")
        .first()
    )


def reject_metadata_suggestion(*, suggestion_id: str) -> MetadataSuggestion | None:
    suggestion = get_metadata_suggestion(suggestion_id)
    if suggestion is None:
        return None
    suggestion.status = "rejected"
    suggestion.updated_at = now_utc()
    suggestion.save(update_fields=["status", "updated_at"])
    return suggestion


def _key_exists(model: Any, *, key: str, exclude_id: str | None = None) -> bool:
    query = model.objects.filter(key=key)
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    return bool(query.exists())


def keyword_key_exists(*, key: str, exclude_id: str | None = None) -> bool:
    return _key_exists(Keyword, key=key, exclude_id=exclude_id)


def tag_key_exists(*, key: str, exclude_id: str | None = None) -> bool:
    return _key_exists(Tag, key=key, exclude_id=exclude_id)


def symbol_key_exists(*, key: str, exclude_id: str | None = None) -> bool:
    return _key_exists(Symbol, key=key, exclude_id=exclude_id)


def type_key_exists(*, key: str, exclude_id: str | None = None) -> bool:
    return _key_exists(Type, key=key, exclude_id=exclude_id)


def create_keyword(*, key: str, label: str, identifiers_json: list[str] | None = None) -> Keyword:
    return Keyword.objects.create(key=key, label=label, identifiers_json=identifiers_json or [])


def create_tag(*, key: str, label: str, identifiers_json: list[str] | None = None) -> Tag:
    return Tag.objects.create(key=key, label=label, identifiers_json=identifiers_json or [])


def create_type(*, key: str, label: str, identifiers_json: list[str] | None = None) -> Type:
    return Type.objects.create(key=key, label=label, identifiers_json=identifiers_json or [])


def get_or_create_metadata_suggestion(
    *,
    kind: str,
    normalized_value: str,
    display_value: str,
) -> MetadataSuggestion:
    suggestion = (
        MetadataSuggestion.objects.filter(kind=kind, normalized_value=normalized_value)
        .select_related("accepted_tag", "accepted_type")
        .first()
    )
    if suggestion is not None:
        if not suggestion.display_value.strip() and display_value.strip():
            suggestion.display_value = display_value
            suggestion.updated_at = now_utc()
            suggestion.save(update_fields=["display_value", "updated_at"])
        return suggestion
    return MetadataSuggestion.objects.create(
        kind=kind,
        normalized_value=normalized_value,
        display_value=display_value,
    )


def append_metadata_identifier(*, entry: Tag | Type, identifier: str) -> None:
    normalized_identifiers = _normalized_identifiers(entry.label, [identifier])
    for existing in entry.identifiers_json:
        normalized = " ".join(str(existing).split()).strip().lower()
        if normalized and normalized not in normalized_identifiers:
            normalized_identifiers.append(normalized)
    entry.identifiers_json = normalized_identifiers
    entry.updated_at = now_utc()
    entry.save(update_fields=["identifiers_json", "updated_at"])


def create_symbol(
    *,
    key: str,
    label: str,
    symbol_type: str,
    detector_type: str,
    detection_config_json: dict[str, object],
    text_enrichment_json: dict[str, object],
    reference_assets_json: list[str],
    text_token: str,
    enabled: bool,
) -> Symbol:
    return Symbol.objects.create(
        key=key,
        label=label,
        symbol_type=symbol_type,
        detector_type=detector_type,
        detection_config_json=detection_config_json,
        text_enrichment_json=text_enrichment_json,
        reference_assets_json=reference_assets_json,
        text_token=text_token,
        enabled=enabled,
    )


def _update(row: MetadataRow, updates: dict[str, object]) -> MetadataRow:
    for field_name, field_value in updates.items():
        setattr(row, field_name, field_value)
    row.updated_at = now_utc()
    row.save()
    return row


def update_keyword(*, entry_id: str, updates: dict[str, object]) -> Keyword | None:
    row = get_keyword(entry_id)
    return None if row is None else _update(row, updates)


def update_tag(*, entry_id: str, updates: dict[str, object]) -> Tag | None:
    row = get_tag(entry_id)
    return None if row is None else _update(row, updates)


def update_type(*, entry_id: str, updates: dict[str, object]) -> Type | None:
    row = get_type(entry_id)
    return None if row is None else _update(row, updates)


def update_symbol(*, entry_id: str, updates: dict[str, object]) -> Symbol | None:
    row = get_symbol(entry_id)
    return None if row is None else _update(row, updates)


def delete_keyword(*, entry_id: str) -> bool:
    deleted, _ = Keyword.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_tag(*, entry_id: str) -> bool:
    deleted, _ = Tag.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_type(*, entry_id: str) -> bool:
    deleted, _ = Type.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_symbol(*, entry_id: str) -> bool:
    deleted, _ = Symbol.objects.filter(id=entry_id).delete()
    return deleted > 0


def _replace_links(link_model: Any, card_version_id: str, field_name: str, ids: list[str]) -> None:
    link_model.objects.filter(card_version_id=card_version_id).delete()
    seen: set[str] = set()
    rows: list[Any] = []
    for row_id in ids:
        if row_id in seen:
            continue
        seen.add(row_id)
        rows.append(link_model(card_version_id=card_version_id, **{field_name: row_id}))
    link_model.objects.bulk_create(rows)


def replace_card_version_keywords(*, card_version_id: str, keyword_ids: list[str]) -> None:
    _replace_links(CardVersionKeyword, card_version_id, "keyword_id", keyword_ids)


def replace_card_version_tags(*, card_version_id: str, tag_ids: list[str]) -> None:
    _replace_links(CardVersionTag, card_version_id, "tag_id", tag_ids)


def replace_card_version_types(*, card_version_id: str, type_ids: list[str]) -> None:
    _replace_links(CardVersionType, card_version_id, "type_id", type_ids)


def replace_card_version_symbols(*, card_version_id: str, symbol_ids: list[str]) -> None:
    _replace_links(CardVersionSymbol, card_version_id, "symbol_id", symbol_ids)


def replace_card_version_metadata_suggestions(
    *,
    card_version_id: str,
    kind: str,
    candidates: list[SuggestionCandidate],
    parse_result_id: str | None = None,
) -> None:
    CardVersionMetadataSuggestion.objects.filter(
        card_version_id=card_version_id,
        suggestion__kind=kind,
    ).delete()

    seen: set[str] = set()
    rows: list[CardVersionMetadataSuggestion] = []
    for candidate in candidates:
        if candidate.normalized_value in seen:
            continue
        seen.add(candidate.normalized_value)
        suggestion = get_or_create_metadata_suggestion(
            kind=kind,
            normalized_value=candidate.normalized_value,
            display_value=candidate.display_value,
        )
        rows.append(
            CardVersionMetadataSuggestion(
                card_version_id=card_version_id,
                suggestion_id=suggestion.id,
                parse_result_id=parse_result_id,
                source_text=candidate.source_text,
                normalized_source_text=candidate.normalized_source_text,
            )
        )
    CardVersionMetadataSuggestion.objects.bulk_create(rows)


def refresh_rule_text_for_symbol(
    *,
    symbol_id: str,
    old_key: str | None = None,
    new_key: str | None = None,
) -> int:
    versions = list(
        CardVersion.objects.filter(card_version_symbols__symbol_id=symbol_id)
        .distinct()
    )
    changed_versions: list[CardVersion] = []

    for version in versions:
        enriched_text = version.rules_text_enriched
        if old_key and new_key and old_key != new_key:
            enriched_text = replace_symbol_placeholder_key(
                enriched_text,
                old_symbol_key=old_key,
                new_symbol_key=new_key,
            )

        symbol_tokens_by_key = {
            symbol.key: symbol.text_token
            for symbol in get_symbols_for_card_version(version.id)
        }
        rendered_text = render_enriched_rule_text(
            enriched_text,
            symbol_tokens_by_key=symbol_tokens_by_key,
        )
        if enriched_text == version.rules_text_enriched and rendered_text == version.rules_text:
            continue

        version.rules_text_enriched = enriched_text
        version.rules_text = rendered_text
        version.updated_at = now_utc()
        changed_versions.append(version)

    if changed_versions:
        CardVersion.objects.bulk_update(
            changed_versions,
            ["rules_text_enriched", "rules_text", "updated_at"],
        )
    return len(changed_versions)


def list_metadata_suggestions(
    *,
    kind: str,
    status: str | None = None,
) -> list[MetadataSuggestionListRow]:
    query = (
        MetadataSuggestion.objects.filter(kind=kind)
        .select_related("accepted_tag", "accepted_type")
        .annotate(
            occurrence_count=Count("card_version_metadata_suggestions", distinct=True)
        )
        .filter(occurrence_count__gt=0)
        .order_by("-occurrence_count", "display_value", "normalized_value")
    )
    if status is not None:
        query = query.filter(status=status)
    return [
        MetadataSuggestionListRow(
            suggestion=row,
            occurrence_count=int(getattr(row, "occurrence_count", 0)),
        )
        for row in query
    ]


def list_keywords_with_linked_card_counts() -> list[Keyword]:
    return list(
        Keyword.objects.order_by("label").annotate(
            linked_card_count=Count(
                "card_version_keywords",
                filter=Q(card_version_keywords__card_version__is_latest=True),
                distinct=True,
            ),
        )
    )


def list_tags_with_linked_card_counts() -> list[Tag]:
    return list(
        Tag.objects.order_by("label").annotate(
            linked_card_count=Count(
                "card_version_tags",
                filter=Q(card_version_tags__card_version__is_latest=True),
                distinct=True,
            ),
        )
    )


def list_types_with_linked_card_counts() -> list[Type]:
    return list(
        Type.objects.order_by("label").annotate(
            linked_card_count=Count(
                "card_version_types",
                filter=Q(card_version_types__card_version__is_latest=True),
                distinct=True,
            ),
        )
    )


def list_symbols_with_linked_card_counts() -> list[Symbol]:
    return list(
        Symbol.objects.order_by("label").annotate(
            linked_card_count=Count(
                "card_version_symbols",
                filter=Q(card_version_symbols__card_version__is_latest=True),
                distinct=True,
            ),
        )
    )


def list_card_version_suggestion_occurrences(
    suggestion_id: str,
) -> list[CardVersionMetadataSuggestion]:
    return list(
        CardVersionMetadataSuggestion.objects.filter(suggestion_id=suggestion_id)
        .select_related("card_version__card", "parse_result")
        .prefetch_related("card_version__images")
        .order_by("-created_at")
    )


def list_latest_versions_for_keyword_detail(*, entry_id: str, limit: int = 12) -> tuple[list[CardVersion], int]:
    return _list_latest_versions_for_detail(
        relation_filter="card_version_keywords__keyword_id",
        entry_id=entry_id,
        limit=limit,
    )


def list_latest_versions_for_tag_detail(*, entry_id: str, limit: int = 12) -> tuple[list[CardVersion], int]:
    return _list_latest_versions_for_detail(
        relation_filter="card_version_tags__tag_id",
        entry_id=entry_id,
        limit=limit,
    )


def list_latest_versions_for_type_detail(*, entry_id: str, limit: int = 12) -> tuple[list[CardVersion], int]:
    return _list_latest_versions_for_detail(
        relation_filter="card_version_types__type_id",
        entry_id=entry_id,
        limit=limit,
    )


def list_latest_versions_for_symbol_detail(*, entry_id: str, limit: int = 12) -> tuple[list[CardVersion], int]:
    return _list_latest_versions_for_detail(
        relation_filter="card_version_symbols__symbol_id",
        entry_id=entry_id,
        limit=limit,
    )


def get_keywords_for_card_version(card_version_id: str) -> list[Keyword]:
    return [row.keyword for row in _keyword_links(card_version_id)]


def get_tags_for_card_version(card_version_id: str) -> list[Tag]:
    return [row.tag for row in _tag_links(card_version_id)]


def get_symbols_for_card_version(card_version_id: str) -> list[Symbol]:
    return [row.symbol for row in _symbol_links(card_version_id)]


def get_types_for_card_version(card_version_id: str) -> list[Type]:
    return [row.type for row in _type_links(card_version_id)]


def get_keywords_for_card_versions(card_version_ids: list[str]) -> dict[str, list[Keyword]]:
    return _group_links_by_card_version(_keyword_links_many(card_version_ids), "keyword")


def get_tags_for_card_versions(card_version_ids: list[str]) -> dict[str, list[Tag]]:
    return _group_links_by_card_version(_tag_links_many(card_version_ids), "tag")


def get_symbols_for_card_versions(card_version_ids: list[str]) -> dict[str, list[Symbol]]:
    return _group_links_by_card_version(_symbol_links_many(card_version_ids), "symbol")


def get_types_for_card_versions(card_version_ids: list[str]) -> dict[str, list[Type]]:
    return _group_links_by_card_version(_type_links_many(card_version_ids), "type")


def _group_links_by_card_version(link_rows: list[Any], relation_name: str) -> dict[str, list[Any]]:
    card_version_ids = {row.card_version_id for row in link_rows}
    grouped: dict[str, list[Any]] = {card_version_id: [] for card_version_id in card_version_ids}
    for row in link_rows:
        grouped.setdefault(row.card_version_id, []).append(getattr(row, relation_name))
    return grouped


def _keyword_links(card_version_id: str) -> list[CardVersionKeyword]:
    return _keyword_links_many([card_version_id])


def _tag_links(card_version_id: str) -> list[CardVersionTag]:
    return _tag_links_many([card_version_id])


def _symbol_links(card_version_id: str) -> list[CardVersionSymbol]:
    return _symbol_links_many([card_version_id])


def _type_links(card_version_id: str) -> list[CardVersionType]:
    return _type_links_many([card_version_id])


def _keyword_links_many(card_version_ids: list[str]) -> list[CardVersionKeyword]:
    return _link_rows(CardVersionKeyword, card_version_ids, "keyword")


def _tag_links_many(card_version_ids: list[str]) -> list[CardVersionTag]:
    return _link_rows(CardVersionTag, card_version_ids, "tag")


def _symbol_links_many(card_version_ids: list[str]) -> list[CardVersionSymbol]:
    return _link_rows(CardVersionSymbol, card_version_ids, "symbol")


def _type_links_many(card_version_ids: list[str]) -> list[CardVersionType]:
    return _link_rows(CardVersionType, card_version_ids, "type")


def _link_rows(link_model: Any, card_version_ids: list[str], relation_name: str) -> list[Any]:
    if not card_version_ids:
        return []
    return list(
        link_model.objects.filter(card_version_id__in=card_version_ids)
        .select_related(relation_name)
        .order_by(f"{relation_name}__label")
    )


def _list_latest_versions_for_detail(
    *,
    relation_filter: str,
    entry_id: str,
    limit: int,
) -> tuple[list[CardVersion], int]:
    versions = (
        CardVersion.objects.filter(is_latest=True, **{relation_filter: entry_id})
        .select_related("card")
        .prefetch_related("images")
        .order_by("-updated_at")
        .distinct()
    )
    return list(versions[:limit]), versions.count()


def _normalized_identifiers(label: str, identifiers: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    canonical_identifier = " ".join(label.split()).strip().lower()
    if canonical_identifier:
        seen.add(canonical_identifier)
        out.append(canonical_identifier)

    if identifiers is None:
        return out

    for raw_identifier in identifiers:
        compact = " ".join(str(raw_identifier).split()).strip().lower()
        if not compact or compact in seen:
            continue
        seen.add(compact)
        out.append(compact)
    return out

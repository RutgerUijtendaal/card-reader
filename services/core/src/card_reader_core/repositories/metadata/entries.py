from __future__ import annotations

from typing import Any

from django.db.models import Case, Count, IntegerField, Q, Value, When

from card_reader_core.models import CardVersion, Keyword, Symbol, Tag, Type, active_card_lifecycle_q, now_utc

from .types import MANA_TYPE_KEY, MetadataRow


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


def list_types_for_card_sort() -> list[Type]:
    return list(
        Type.objects.annotate(
            linked_card_count=Count(
                "card_version_types",
                filter=Q(card_version_types__card_version__is_latest=True)
                & active_card_lifecycle_q(
                    field_path="card_version_types__card_version__card__lifecycle_status",
                ),
                distinct=True,
            ),
            type_sort_is_mana=Case(
                When(key__iexact=MANA_TYPE_KEY, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        ).order_by(
            "type_sort_is_mana",
            "-linked_card_count",
            "label",
            "id",
        )
    )


def get_keyword(entry_id: str) -> Keyword | None:
    return Keyword.objects.filter(id=entry_id).first()


def get_tag(entry_id: str) -> Tag | None:
    return Tag.objects.filter(id=entry_id).first()


def get_symbol(entry_id: str) -> Symbol | None:
    return Symbol.objects.filter(id=entry_id).first()


def get_type(entry_id: str) -> Type | None:
    return Type.objects.filter(id=entry_id).first()


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


def append_metadata_identifier(*, entry: Tag | Type, identifier: str) -> None:
    normalized_identifiers = _normalized_identifiers(entry.label, [identifier])
    for existing in entry.identifiers_json:
        normalized = " ".join(str(existing).split()).strip().lower()
        if normalized and normalized not in normalized_identifiers:
            normalized_identifiers.append(normalized)
    entry.identifiers_json = normalized_identifiers
    entry.updated_at = now_utc()
    entry.save(update_fields=["identifiers_json", "updated_at"])


def list_keywords_with_linked_card_counts() -> list[Keyword]:
    return list(
        Keyword.objects.order_by("label").annotate(
            linked_card_count=Count(
                "card_version_keywords",
                filter=Q(card_version_keywords__card_version__is_latest=True)
                & active_card_lifecycle_q(
                    field_path="card_version_keywords__card_version__card__lifecycle_status",
                ),
                distinct=True,
            ),
        )
    )


def list_tags_with_linked_card_counts() -> list[Tag]:
    return list(
        Tag.objects.order_by("label").annotate(
            linked_card_count=Count(
                "card_version_tags",
                filter=Q(card_version_tags__card_version__is_latest=True)
                & active_card_lifecycle_q(
                    field_path="card_version_tags__card_version__card__lifecycle_status",
                ),
                distinct=True,
            ),
        )
    )


def list_types_with_linked_card_counts() -> list[Type]:
    return list(
        Type.objects.order_by("label").annotate(
            linked_card_count=Count(
                "card_version_types",
                filter=Q(card_version_types__card_version__is_latest=True)
                & active_card_lifecycle_q(
                    field_path="card_version_types__card_version__card__lifecycle_status",
                ),
                distinct=True,
            ),
        )
    )


def list_symbols_with_linked_card_counts() -> list[Symbol]:
    return list(
        Symbol.objects.order_by("label").annotate(
            linked_card_count=Count(
                "card_version_symbols",
                filter=Q(card_version_symbols__card_version__is_latest=True)
                & active_card_lifecycle_q(
                    field_path="card_version_symbols__card_version__card__lifecycle_status",
                ),
                distinct=True,
            ),
        )
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


def _list_latest_versions_for_detail(
    *,
    relation_filter: str,
    entry_id: str,
    limit: int,
) -> tuple[list[CardVersion], int]:
    versions = (
        CardVersion.objects.filter(is_latest=True, **{relation_filter: entry_id})
        .filter(active_card_lifecycle_q())
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

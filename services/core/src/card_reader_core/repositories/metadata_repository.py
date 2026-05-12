from __future__ import annotations

from collections import defaultdict
from typing import Any, TypeVar

from card_reader_core.models import (
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Keyword,
    Symbol,
    Tag,
    Type,
    now_utc,
)

MetadataModel = Keyword | Tag | Symbol | Type
MetadataRow = TypeVar("MetadataRow", bound=MetadataModel)


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


def create_keyword(*, key: str, label: str, identifiers_json: str = "[]") -> Keyword:
    return Keyword.objects.create(key=key, label=label, identifiers_json=identifiers_json)


def create_tag(*, key: str, label: str, identifiers_json: str = "[]") -> Tag:
    return Tag.objects.create(key=key, label=label, identifiers_json=identifiers_json)


def create_type(*, key: str, label: str, identifiers_json: str = "[]") -> Type:
    return Type.objects.create(key=key, label=label, identifiers_json=identifiers_json)


def create_symbol(
    *,
    key: str,
    label: str,
    symbol_type: str,
    detector_type: str,
    detection_config_json: str,
    reference_assets_json: str,
    text_token: str,
    enabled: bool,
) -> Symbol:
    return Symbol.objects.create(
        key=key,
        label=label,
        symbol_type=symbol_type,
        detector_type=detector_type,
        detection_config_json=detection_config_json,
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
    CardVersionKeyword.objects.filter(keyword_id=entry_id).delete()
    deleted, _ = Keyword.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_tag(*, entry_id: str) -> bool:
    CardVersionTag.objects.filter(tag_id=entry_id).delete()
    deleted, _ = Tag.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_type(*, entry_id: str) -> bool:
    CardVersionType.objects.filter(type_id=entry_id).delete()
    deleted, _ = Type.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_symbol(*, entry_id: str) -> bool:
    CardVersionSymbol.objects.filter(symbol_id=entry_id).delete()
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


def get_keywords_for_card_version(card_version_id: str) -> list[Keyword]:
    ids = CardVersionKeyword.objects.filter(card_version_id=card_version_id).values_list("keyword_id", flat=True)
    return list(Keyword.objects.filter(id__in=ids).order_by("label"))


def get_tags_for_card_version(card_version_id: str) -> list[Tag]:
    ids = CardVersionTag.objects.filter(card_version_id=card_version_id).values_list("tag_id", flat=True)
    return list(Tag.objects.filter(id__in=ids).order_by("label"))


def get_symbols_for_card_version(card_version_id: str) -> list[Symbol]:
    ids = CardVersionSymbol.objects.filter(card_version_id=card_version_id).values_list("symbol_id", flat=True)
    return list(Symbol.objects.filter(id__in=ids).order_by("label"))


def get_types_for_card_version(card_version_id: str) -> list[Type]:
    ids = CardVersionType.objects.filter(card_version_id=card_version_id).values_list("type_id", flat=True)
    return list(Type.objects.filter(id__in=ids).order_by("label"))


def get_keywords_for_card_versions(card_version_ids: list[str]) -> dict[str, list[Keyword]]:
    return _get_metadata_for_card_versions(
        card_version_ids,
        CardVersionKeyword,
        "keyword_id",
        Keyword,
    )


def get_tags_for_card_versions(card_version_ids: list[str]) -> dict[str, list[Tag]]:
    return _get_metadata_for_card_versions(
        card_version_ids,
        CardVersionTag,
        "tag_id",
        Tag,
    )


def get_symbols_for_card_versions(card_version_ids: list[str]) -> dict[str, list[Symbol]]:
    return _get_metadata_for_card_versions(
        card_version_ids,
        CardVersionSymbol,
        "symbol_id",
        Symbol,
    )


def get_types_for_card_versions(card_version_ids: list[str]) -> dict[str, list[Type]]:
    return _get_metadata_for_card_versions(
        card_version_ids,
        CardVersionType,
        "type_id",
        Type,
    )


def _get_metadata_for_card_versions(
    card_version_ids: list[str],
    link_model: Any,
    metadata_field_name: str,
    metadata_model: Any,
) -> dict[str, list[Any]]:
    if not card_version_ids:
        return {}

    link_rows = list(
        link_model.objects.filter(card_version_id__in=card_version_ids)
        .values("card_version_id", metadata_field_name)
    )
    metadata_ids = {str(row[metadata_field_name]) for row in link_rows if row.get(metadata_field_name)}
    if not metadata_ids:
        return {card_version_id: [] for card_version_id in card_version_ids}

    metadata_by_id = {
        str(row.id): row
        for row in metadata_model.objects.filter(id__in=metadata_ids).order_by("label")
    }
    grouped_ids: dict[str, set[str]] = defaultdict(set)
    for row in link_rows:
        card_version_id = str(row["card_version_id"])
        metadata_id = str(row[metadata_field_name])
        if metadata_id in metadata_by_id:
            grouped_ids[card_version_id].add(metadata_id)

    out: dict[str, list[Any]] = {}
    for card_version_id in card_version_ids:
        ordered_rows = [
            row for row in metadata_by_id.values() if str(row.id) in grouped_ids.get(card_version_id, set())
        ]
        out[card_version_id] = ordered_rows
    return out

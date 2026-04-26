from __future__ import annotations

from typing import Any, TypeVar

from .helpers import normalize_slug_key
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


def list_keywords(_session: Any = None, *, keys: set[str] | None = None) -> list[Keyword]:
    return _list(Keyword, keys=keys)


def list_tags(_session: Any = None, *, keys: set[str] | None = None) -> list[Tag]:
    return _list(Tag, keys=keys)


def list_symbols(_session: Any = None, *, keys: set[str] | None = None) -> list[Symbol]:
    return _list(Symbol, keys=keys)


def list_detectable_symbols(_session: Any = None) -> list[Symbol]:
    return list(Symbol.objects.filter(enabled=True, detector_type="template").order_by("label"))


def list_types(_session: Any = None, *, keys: set[str] | None = None) -> list[Type]:
    return _list(Type, keys=keys)


def get_keyword(_session: Any, entry_id: str) -> Keyword | None:
    return Keyword.objects.filter(id=entry_id).first()


def get_tag(_session: Any, entry_id: str) -> Tag | None:
    return Tag.objects.filter(id=entry_id).first()


def get_symbol(_session: Any, entry_id: str) -> Symbol | None:
    return Symbol.objects.filter(id=entry_id).first()


def get_type(_session: Any, entry_id: str) -> Type | None:
    return Type.objects.filter(id=entry_id).first()


def _key_exists(model: Any, *, key: str, exclude_id: str | None = None) -> bool:
    query = model.objects.filter(key=key)
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    return bool(query.exists())


def keyword_key_exists(_session: Any, *, key: str, exclude_id: str | None = None) -> bool:
    return _key_exists(Keyword, key=key, exclude_id=exclude_id)


def tag_key_exists(_session: Any, *, key: str, exclude_id: str | None = None) -> bool:
    return _key_exists(Tag, key=key, exclude_id=exclude_id)


def symbol_key_exists(_session: Any, *, key: str, exclude_id: str | None = None) -> bool:
    return _key_exists(Symbol, key=key, exclude_id=exclude_id)


def type_key_exists(_session: Any, *, key: str, exclude_id: str | None = None) -> bool:
    return _key_exists(Type, key=key, exclude_id=exclude_id)


def create_keyword(_session: Any, *, key: str, label: str) -> Keyword:
    return Keyword.objects.create(key=key, label=label)


def create_tag(_session: Any, *, key: str, label: str) -> Tag:
    return Tag.objects.create(key=key, label=label)


def create_type(_session: Any, *, key: str, label: str) -> Type:
    return Type.objects.create(key=key, label=label)


def create_symbol(
    _session: Any,
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


def update_keyword(_session: Any, *, entry_id: str, updates: dict[str, object]) -> Keyword | None:
    row = get_keyword(None, entry_id)
    return None if row is None else _update(row, updates)


def update_tag(_session: Any, *, entry_id: str, updates: dict[str, object]) -> Tag | None:
    row = get_tag(None, entry_id)
    return None if row is None else _update(row, updates)


def update_type(_session: Any, *, entry_id: str, updates: dict[str, object]) -> Type | None:
    row = get_type(None, entry_id)
    return None if row is None else _update(row, updates)


def update_symbol(_session: Any, *, entry_id: str, updates: dict[str, object]) -> Symbol | None:
    row = get_symbol(None, entry_id)
    return None if row is None else _update(row, updates)


def delete_keyword(_session: Any, *, entry_id: str) -> bool:
    CardVersionKeyword.objects.filter(keyword_id=entry_id).delete()
    deleted, _ = Keyword.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_tag(_session: Any, *, entry_id: str) -> bool:
    CardVersionTag.objects.filter(tag_id=entry_id).delete()
    deleted, _ = Tag.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_type(_session: Any, *, entry_id: str) -> bool:
    CardVersionType.objects.filter(type_id=entry_id).delete()
    deleted, _ = Type.objects.filter(id=entry_id).delete()
    return deleted > 0


def delete_symbol(_session: Any, *, entry_id: str) -> bool:
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


def replace_card_version_keywords(_session: Any, *, card_version_id: str, keyword_ids: list[str]) -> None:
    _replace_links(CardVersionKeyword, card_version_id, "keyword_id", keyword_ids)


def replace_card_version_tags(_session: Any, *, card_version_id: str, tag_ids: list[str]) -> None:
    _replace_links(CardVersionTag, card_version_id, "tag_id", tag_ids)


def replace_card_version_types(_session: Any, *, card_version_id: str, type_ids: list[str]) -> None:
    _replace_links(CardVersionType, card_version_id, "type_id", type_ids)


def replace_card_version_symbols(_session: Any, *, card_version_id: str, symbol_ids: list[str]) -> None:
    _replace_links(CardVersionSymbol, card_version_id, "symbol_id", symbol_ids)


def upsert_tags_by_labels(_session: Any, labels: list[str]) -> list[Tag]:
    return _upsert_labels(Tag, labels)


def upsert_types_by_labels(_session: Any, labels: list[str]) -> list[Type]:
    return _upsert_labels(Type, labels)


def _upsert_labels(model: Any, labels: list[str]) -> list[Any]:
    out: list[Any] = []
    for key, label in _normalize_label_entries(labels):
        row, created = model.objects.get_or_create(key=key, defaults={"label": label})
        if not created and row.label != label:
            row.label = label
            row.updated_at = now_utc()
            row.save(update_fields=["label", "updated_at"])
        out.append(row)
    return out


def get_keywords_for_card_version(_session: Any, card_version_id: str) -> list[Keyword]:
    ids = CardVersionKeyword.objects.filter(card_version_id=card_version_id).values_list("keyword_id", flat=True)
    return list(Keyword.objects.filter(id__in=ids).order_by("label"))


def get_tags_for_card_version(_session: Any, card_version_id: str) -> list[Tag]:
    ids = CardVersionTag.objects.filter(card_version_id=card_version_id).values_list("tag_id", flat=True)
    return list(Tag.objects.filter(id__in=ids).order_by("label"))


def get_symbols_for_card_version(_session: Any, card_version_id: str) -> list[Symbol]:
    ids = CardVersionSymbol.objects.filter(card_version_id=card_version_id).values_list("symbol_id", flat=True)
    return list(Symbol.objects.filter(id__in=ids).order_by("label"))


def get_types_for_card_version(_session: Any, card_version_id: str) -> list[Type]:
    ids = CardVersionType.objects.filter(card_version_id=card_version_id).values_list("type_id", flat=True)
    return list(Type.objects.filter(id__in=ids).order_by("label"))


def _normalize_label_entries(labels: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in labels:
        label = " ".join(raw.split()).strip()
        if not label:
            continue
        key = normalize_slug_key(label)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((key, label))
    return out

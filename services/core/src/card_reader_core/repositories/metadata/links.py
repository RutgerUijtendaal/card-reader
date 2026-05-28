from __future__ import annotations

from typing import Any

from card_reader_core.models import (
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Keyword,
    Symbol,
    Tag,
    Type,
)


def replace_card_version_keywords(*, card_version_id: str, keyword_ids: list[str]) -> None:
    _replace_links(CardVersionKeyword, card_version_id, "keyword_id", keyword_ids)


def replace_card_version_tags(*, card_version_id: str, tag_ids: list[str]) -> None:
    _replace_links(CardVersionTag, card_version_id, "tag_id", tag_ids)


def replace_card_version_types(*, card_version_id: str, type_ids: list[str]) -> None:
    _replace_links(CardVersionType, card_version_id, "type_id", type_ids)


def replace_card_version_symbols(*, card_version_id: str, symbol_ids: list[str]) -> None:
    _replace_links(CardVersionSymbol, card_version_id, "symbol_id", symbol_ids)


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

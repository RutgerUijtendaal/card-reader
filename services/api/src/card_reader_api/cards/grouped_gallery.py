from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, TypedDict

from card_reader_api.card_groups.serializers import card_group_gallery_payload, card_group_visible_members
from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import CardListFilterParams, card_payload
from card_reader_core.repositories.cards import (
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_TYPES_ASC,
    get_card_list_rows_by_version_ids,
    list_matching_card_candidates,
)
from card_reader_core.repositories.metadata import list_types_for_card_sort
from card_reader_core.services.card_groups import CardGroupService
from card_reader_core.services.cards import get_card_versions_metadata

if TYPE_CHECKING:
    from card_reader_core.models import CardGroup
    from card_reader_core.models import Type
    from card_reader_core.repositories.cards import CardLifecycleFilter, CardSort

MANA_TYPE_KEY = "mana"


class GroupedGalleryItem(TypedDict):
    result_type: Literal["card", "card_group"]
    item_id: str
    card_version_id: str | None
    group_id: str | None
    label: str
    name: str
    mana_value: int | None
    updated_at: datetime
    types: list["Type"]


def grouped_gallery_payload(filters: CardListFilterParams) -> dict[str, object]:
    page = filters["page"]
    page_size = filters["page_size"]
    matching_rows = list_matching_card_candidates(
        query=filters["query"],
        card_ids=filters["card_ids"],
        max_confidence=filters["max_confidence"],
        keyword_ids=filters["keyword_ids"],
        keyword_match=filters["keyword_match"],
        tag_ids=filters["tag_ids"],
        tag_match=filters["tag_match"],
        mana_symbol_ids=filters["mana_symbol_ids"],
        mana_symbol_exclude_ids=filters["mana_symbol_exclude_ids"],
        mana_symbol_match=filters["mana_symbol_match"],
        affinity_symbol_ids=filters["affinity_symbol_ids"],
        affinity_symbol_exclude_ids=filters["affinity_symbol_exclude_ids"],
        affinity_symbol_match=filters["affinity_symbol_match"],
        devotion_symbol_ids=filters["devotion_symbol_ids"],
        devotion_symbol_exclude_ids=filters["devotion_symbol_exclude_ids"],
        devotion_symbol_match=filters["devotion_symbol_match"],
        other_symbol_ids=filters["other_symbol_ids"],
        other_symbol_exclude_ids=filters["other_symbol_exclude_ids"],
        other_symbol_match=filters["other_symbol_match"],
        symbol_ids=filters["symbol_ids"],
        type_ids=filters["type_ids"],
        type_match=filters["type_match"],
        mana_cost_min=filters["mana_cost_min"],
        mana_cost_max=filters["mana_cost_max"],
        template_id=filters["template_id"],
        is_hero=filters["is_hero"],
        attack_min=filters["attack_min"],
        attack_max=filters["attack_max"],
        health_min=filters["health_min"],
        health_max=filters["health_max"],
        lifecycle_status=filters["lifecycle_status"],
        sort=filters["sort"],
    )
    matching_card_ids = [row.version.card.id for row in matching_rows]
    groups = CardGroupService().get_groups_for_cards(matching_card_ids)
    lifecycle_status = filters["lifecycle_status"]

    participant_card_ids = {
        member.card.id
        for group in groups
        for member in card_group_visible_members(group, lifecycle_status)
    }

    grouped_items: list[GroupedGalleryItem] = []
    for row in matching_rows:
        if row.version.card.id in participant_card_ids:
            continue
        grouped_items.append(
            _build_grouped_gallery_item(
                result_type="card",
                item_id=row.version.card.id,
                card_version_id=row.version.id,
                group_id=None,
                label=row.version.card.label,
                name=row.version.name,
                mana_value=row.version.mana_value,
                updated_at=row.version.updated_at,
                types=row.types,
            )
        )

    anchor_versions = {
        group.id: group.anchor_card.latest_version
        for group in groups
        if group.anchor_card.latest_version is not None
    }
    anchor_metadata = (
        get_card_versions_metadata([version.id for version in anchor_versions.values()])
        if filters["sort"] == CARD_SORT_TYPES_ASC
        else {}
    )
    for group in groups:
        anchor_version = anchor_versions.get(group.id)
        member_ids = {member.card.id for member in card_group_visible_members(group, lifecycle_status)}
        if anchor_version is None or not member_ids.intersection(matching_card_ids):
            continue
        grouped_items.append(
            _build_grouped_gallery_item(
                result_type="card_group",
                item_id=group.id,
                card_version_id=None,
                group_id=group.id,
                label=group.anchor_card.label,
                name=anchor_version.name,
                mana_value=anchor_version.mana_value,
                updated_at=anchor_version.updated_at,
                types=anchor_metadata.get(anchor_version.id, {"types": []})["types"],
            )
        )

    type_sort_lookup = _build_type_sort_lookup() if filters["sort"] == CARD_SORT_TYPES_ASC else None
    grouped_items.sort(key=lambda row: _grouped_gallery_sort_key(row, filters["sort"], type_sort_lookup))
    total_count = len(grouped_items)
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    offset = (normalized_page - 1) * normalized_page_size
    page_items = grouped_items[offset : offset + normalized_page_size]
    results = _hydrate_grouped_gallery_payloads(page_items, groups, lifecycle_status)
    return {
        "count": total_count,
        "next_page": normalized_page + 1 if normalized_page * normalized_page_size < total_count else None,
        "previous_page": normalized_page - 1 if normalized_page > 1 else None,
        "page": normalized_page,
        "page_size": normalized_page_size,
        "results": results,
    }


def _build_grouped_gallery_item(
    *,
    result_type: Literal["card", "card_group"],
    item_id: str,
    card_version_id: str | None,
    group_id: str | None,
    label: str,
    name: str,
    mana_value: int | None,
    updated_at: datetime,
    types: list["Type"],
) -> GroupedGalleryItem:
    return {
        "result_type": result_type,
        "item_id": item_id,
        "card_version_id": card_version_id,
        "group_id": group_id,
        "label": label,
        "name": name,
        "mana_value": mana_value,
        "updated_at": updated_at,
        "types": types,
    }


def _hydrate_grouped_gallery_payloads(
    page_items: list[GroupedGalleryItem],
    groups: list["CardGroup"],
    lifecycle_status: "CardLifecycleFilter",
) -> list[dict[str, object]]:
    card_version_ids = [
        item["card_version_id"]
        for item in page_items
        if item["result_type"] == "card" and item["card_version_id"] is not None
    ]
    card_payloads_by_version_id = {
        row.version.id: card_payload(
            row.version.card,
            row.version,
            image_url=card_image_asset_url(row.image, fallback_url=f"/cards/{row.version.card.id}/image"),
            metadata={
                "keywords": row.keywords,
                "tags": row.tags,
                "symbols": row.symbols,
                "types": row.types,
            },
        )
        for row in get_card_list_rows_by_version_ids(card_version_ids)
    }
    groups_by_id = {str(group.id): group for group in groups}

    payloads: list[dict[str, object]] = []
    for item in page_items:
        if item["result_type"] == "card":
            version_id = item["card_version_id"]
            if version_id is not None and version_id in card_payloads_by_version_id:
                payloads.append(card_payloads_by_version_id[version_id])
            continue
        group_id = item["group_id"]
        group = groups_by_id.get(group_id or "")
        if group is not None:
            payloads.append(card_group_gallery_payload(group, lifecycle_status=lifecycle_status))
    return payloads


def _grouped_gallery_sort_key(
    item: GroupedGalleryItem,
    sort: CardSort,
    type_sort_lookup: dict[str, tuple[int, str]] | None = None,
) -> tuple[object, ...]:
    item_id = item["item_id"]
    label = item["label"].casefold()
    name = item["name"].casefold()
    mana_value = item["mana_value"]
    updated_at = item["updated_at"]

    if sort == CARD_SORT_NAME_ASC:
        return (name, label, item_id)
    if sort == CARD_SORT_MANA_ASC:
        return (mana_value is None, mana_value if mana_value is not None else 0, name, item_id)
    if sort == CARD_SORT_MANA_DESC:
        return (mana_value is None, -(mana_value if mana_value is not None else 0), name, item_id)
    if sort == CARD_SORT_TYPES_ASC:
        bucket, linked_card_count, type_label = _grouped_gallery_type_sort_value(item["types"], type_sort_lookup)
        return (bucket, -linked_card_count, type_label, name, label, item_id)
    return (-updated_at.timestamp(), label, item_id)


def _build_type_sort_lookup() -> dict[str, tuple[int, str]]:
    lookup: dict[str, tuple[int, str]] = {}
    for row in list_types_for_card_sort():
        key = str(row.key).strip().casefold()
        lookup[key] = (int(getattr(row, "linked_card_count", 0)), str(row.label).casefold())
    return lookup


def _grouped_gallery_type_sort_value(
    types: list["Type"],
    type_sort_lookup: dict[str, tuple[int, str]] | None,
) -> tuple[int, int, str]:
    if not types:
        return (1, 0, "")

    best_value: tuple[int, int, str] | None = None
    for row in types:
        key = str(row.key).strip().casefold()
        label = str(row.label).casefold()
        if key == MANA_TYPE_KEY:
            candidate = (2, 0, label)
        else:
            linked_card_count, ranked_label = (type_sort_lookup or {}).get(key, (0, label))
            candidate = (0, -linked_card_count, ranked_label)
        if best_value is None or candidate < best_value:
            best_value = candidate

    if best_value is None:
        return (1, 0, "")
    return (best_value[0], -best_value[1], best_value[2])

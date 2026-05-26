from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict, cast

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from card_reader_api.card_groups.serializers import card_group_gallery_payload
from card_reader_api.cards.file_views import file_response, immutable_card_image_response, symbol_asset_response
from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import (
    CardListFilterParams,
    CardFiltersQuerySerializer,
    LatestCardReparseSerializer,
    LatestVersionUpdateSerializer,
    card_group_summary_payload,
    card_payload,
    metadata_option,
    symbol_option,
)
from card_reader_api.cards.services import CardActionService, CardReparseError
from card_reader_core.repositories.cards_repository import (
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_TYPES_ASC,
    get_card,
    get_card_image,
    list_card_generations,
    list_cards,
    list_matching_cards,
    update_latest_card_version,
)
from card_reader_core.repositories.metadata_repository import list_types_for_card_sort
from card_reader_core.services.card_groups import CardGroupService
from card_reader_core.services.cards import (
    get_card_version_edit_state,
    get_card_versions_metadata,
    get_card_version_metadata,
    get_card_with_image,
    get_filter_metadata,
    resolve_card_image_path,
)

if TYPE_CHECKING:
    from card_reader_core.models import Type
    from card_reader_core.repositories.cards_repository import CardSort

MANA_TYPE_KEY = "mana"


class GroupedGalleryItem(TypedDict):
    item_id: str
    label: str
    name: str
    mana_value: int | None
    updated_at: datetime
    types: list["Type"]
    payload: dict[str, object]


class CardListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        serializer = CardFiltersQuerySerializer(data=_query_data(request, include_paging=True))
        if not serializer.is_valid():
            return _serializer_error(serializer)
        filters = serializer.validated_list_filters()
        show_groups = filters["show_groups"]
        if show_groups:
            return Response(_grouped_gallery_payload(filters))
        cards = list_cards(
            query=filters["query"],
            card_ids=filters["card_ids"],
            max_confidence=filters["max_confidence"],
            keyword_ids=filters["keyword_ids"],
            keyword_match=filters["keyword_match"],
            tag_ids=filters["tag_ids"],
            tag_match=filters["tag_match"],
            mana_symbol_ids=filters["mana_symbol_ids"],
            mana_symbol_match=filters["mana_symbol_match"],
            affinity_symbol_ids=filters["affinity_symbol_ids"],
            affinity_symbol_match=filters["affinity_symbol_match"],
            devotion_symbol_ids=filters["devotion_symbol_ids"],
            devotion_symbol_match=filters["devotion_symbol_match"],
            other_symbol_ids=filters["other_symbol_ids"],
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
            sort=filters["sort"],
            page=filters["page"],
            page_size=filters["page_size"],
        )
        payloads = []
        for row in cards.results:
            payloads.append(
                card_payload(
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
            )
        return Response(
            {
                "count": cards.count,
                "next_page": cards.page + 1 if cards.page * cards.page_size < cards.count else None,
                "previous_page": cards.page - 1 if cards.page > 1 else None,
                "page": cards.page,
                "page_size": cards.page_size,
                "results": payloads,
            }
        )


class CardFiltersView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        metadata = get_filter_metadata()
        return Response(
            {
                "keywords": [metadata_option(row) for row in metadata["keywords"]],
                "tags": [metadata_option(row) for row in metadata["tags"]],
                "symbols": [symbol_option(row) for row in metadata["symbols"]],
                "types": [metadata_option(row) for row in metadata["types"]],
            }
        )


class CardDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, card_id: str) -> Response:
        card, version, image = get_card_with_image(card_id)
        if card is None or version is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)
        metadata = get_card_version_metadata(version.id)
        edit_state = get_card_version_edit_state(version)
        card_groups = [
            card_group_summary_payload(group, card_id=card.id)
            for group in CardGroupService().get_groups_for_card(card.id)
        ]
        return Response(
            card_payload(
                card,
                version,
                image_url=card_image_asset_url(image, fallback_url=f"/cards/{card.id}/image"),
                metadata=metadata,
                edit_state=edit_state,
                card_groups=card_groups,
            )
        )


class CardGenerationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, card_id: str) -> Response:
        card = get_card(card_id)
        if card is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        versions = list_card_generations(card_id)
        if not versions:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        payloads = []
        for version in versions:
            image = get_card_image(version.id)
            metadata = get_card_version_metadata(version.id)
            edit_state = get_card_version_edit_state(version)
            payloads.append(
                card_payload(
                    card,
                    version,
                    image_url=card_image_asset_url(image, fallback_url=f"/cards/{card_id}/versions/{version.id}/image"),
                    metadata=metadata,
                    edit_state=edit_state,
                )
            )
        return Response(payloads)


class LatestCardVersionUpdateView(APIView):
    def patch(self, request: Request, card_id: str) -> Response:
        serializer = LatestVersionUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_error(serializer)

        updated = update_latest_card_version(
            card_id=card_id,
            updates=serializer.validated_update_payload(),
            restore_fields=serializer.validated_data["restore_fields"],
            restore_metadata_groups=serializer.validated_data["restore_metadata_groups"],
            unlock_fields=serializer.validated_data["unlock_fields"],
            unlock_metadata_groups=serializer.validated_data["unlock_metadata_groups"],
        )
        if updated is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        card, version = updated
        image = get_card_image(version.id)
        metadata = get_card_version_metadata(version.id)
        edit_state = get_card_version_edit_state(version)
        return Response(
            card_payload(
                card,
                version,
                image_url=card_image_asset_url(image, fallback_url=f"/cards/{card_id}/versions/{version.id}/image"),
                metadata=metadata,
                edit_state=edit_state,
            )
        )


class LatestCardReparseView(APIView):
    def post(self, request: Request, card_id: str) -> Response:
        serializer = LatestCardReparseSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        try:
            result = CardActionService().queue_latest_version_reparse(
                card_id,
                template_id=serializer.validated_data.get("template_id"),
            )
        except CardReparseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if result is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "job_id": result.job_id,
                "message": result.message,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CardImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, card_id: str) -> FileResponse:
        card, _version, image = get_card_with_image(card_id)
        if card is None or image is None:
            raise Http404("Card image not found")
        image_path = resolve_card_image_path(image)
        if image_path is None:
            raise Http404("Card image file is missing")
        return file_response(image_path, "Card image file is missing")


class CardVersionImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, card_id: str, version_id: str) -> FileResponse:
        if get_card(card_id) is None:
            raise Http404("Card not found")
        image = get_card_image(version_id)
        if image is None:
            raise Http404("Card image not found")
        image_path = resolve_card_image_path(image)
        if image_path is None:
            raise Http404("Card image file is missing")
        return file_response(image_path, "Card image file is missing")


class ImmutableCardImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, relative_path: str) -> FileResponse:
        return immutable_card_image_response(relative_path)


class SymbolAssetView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, asset_path: str) -> FileResponse:
        return symbol_asset_response(asset_path)


def _query_data(request: Request, *, include_paging: bool) -> dict[str, object]:
    data: dict[str, object] = {
        "query": request.query_params.get("q"),
        "card_ids": request.query_params.getlist("card_ids"),
        "max_confidence": request.query_params.get("max_confidence"),
        "keyword_ids": request.query_params.getlist("keyword_ids"),
        "keyword_match": request.query_params.get("keyword_match"),
        "tag_ids": request.query_params.getlist("tag_ids"),
        "tag_match": request.query_params.get("tag_match"),
        "mana_symbol_ids": request.query_params.getlist("mana_symbol_ids"),
        "mana_symbol_match": request.query_params.get("mana_symbol_match"),
        "affinity_symbol_ids": request.query_params.getlist("affinity_symbol_ids"),
        "affinity_symbol_match": request.query_params.get("affinity_symbol_match"),
        "devotion_symbol_ids": request.query_params.getlist("devotion_symbol_ids"),
        "devotion_symbol_match": request.query_params.get("devotion_symbol_match"),
        "other_symbol_ids": request.query_params.getlist("other_symbol_ids"),
        "other_symbol_match": request.query_params.get("other_symbol_match"),
        "symbol_ids": request.query_params.getlist("symbol_ids"),
        "type_ids": request.query_params.getlist("type_ids"),
        "type_match": request.query_params.get("type_match"),
        "mana_cost_min": request.query_params.get("mana_cost_min"),
        "mana_cost_max": request.query_params.get("mana_cost_max"),
        "template_id": request.query_params.get("template_id"),
        "is_hero": request.query_params.get("is_hero"),
        "attack_min": request.query_params.get("attack_min"),
        "attack_max": request.query_params.get("attack_max"),
        "health_min": request.query_params.get("health_min"),
        "health_max": request.query_params.get("health_max"),
    }
    sort = request.query_params.get("sort")
    if sort is not None:
        data["sort"] = sort
    show_groups = request.query_params.get("show_groups")
    if show_groups is not None:
        data["show_groups"] = show_groups
    if include_paging:
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        if page is not None:
            data["page"] = page
        if page_size is not None:
            data["page_size"] = page_size
    return data


def _serializer_error(serializer: BaseSerializer[Any]) -> Response:
    errors = serializer.errors
    detail = next(iter(cast(Mapping[str, object], errors).values()), "Invalid request.")
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)


def _grouped_gallery_payload(filters: CardListFilterParams) -> dict[str, object]:
    page = filters["page"]
    page_size = filters["page_size"]
    matching_rows = list_matching_cards(
        query=filters["query"],
        card_ids=filters["card_ids"],
        max_confidence=filters["max_confidence"],
        keyword_ids=filters["keyword_ids"],
        keyword_match=filters["keyword_match"],
        tag_ids=filters["tag_ids"],
        tag_match=filters["tag_match"],
        mana_symbol_ids=filters["mana_symbol_ids"],
        mana_symbol_match=filters["mana_symbol_match"],
        affinity_symbol_ids=filters["affinity_symbol_ids"],
        affinity_symbol_match=filters["affinity_symbol_match"],
        devotion_symbol_ids=filters["devotion_symbol_ids"],
        devotion_symbol_match=filters["devotion_symbol_match"],
        other_symbol_ids=filters["other_symbol_ids"],
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
        sort=filters["sort"],
    )
    matching_card_ids = [row.version.card.id for row in matching_rows]
    groups = CardGroupService().get_groups_for_cards(matching_card_ids)

    participant_card_ids = {
        member.card.id
        for group in groups
        for member in group.members.all()
    }

    grouped_items: list[GroupedGalleryItem] = []
    for row in matching_rows:
        if row.version.card.id in participant_card_ids:
            continue
        grouped_items.append(
            _build_grouped_gallery_item(
                item_id=row.version.card.id,
                label=row.version.card.label,
                name=row.version.name,
                mana_value=row.version.mana_value,
                updated_at=row.version.updated_at,
                types=row.types,
                payload=card_payload(
                    row.version.card,
                    row.version,
                    image_url=card_image_asset_url(row.image, fallback_url=f"/cards/{row.version.card.id}/image"),
                    metadata={
                        "keywords": row.keywords,
                        "tags": row.tags,
                        "symbols": row.symbols,
                        "types": row.types,
                    },
                ),
            )
        )

    anchor_versions = {
        group.id: group.anchor_card.latest_version
        for group in groups
        if group.anchor_card.latest_version is not None
    }
    anchor_metadata = get_card_versions_metadata([version.id for version in anchor_versions.values()])
    for group in groups:
        anchor_version = anchor_versions.get(group.id)
        member_ids = {member.card.id for member in group.members.all()}
        if anchor_version is None or not member_ids.intersection(matching_card_ids):
            continue
        grouped_items.append(
            _build_grouped_gallery_item(
                item_id=group.id,
                label=group.anchor_card.label,
                name=anchor_version.name,
                mana_value=anchor_version.mana_value,
                updated_at=anchor_version.updated_at,
                types=anchor_metadata.get(anchor_version.id, {"types": []})["types"],
                payload=card_group_gallery_payload(group),
            )
        )

    type_sort_lookup = _build_type_sort_lookup() if filters["sort"] == CARD_SORT_TYPES_ASC else None
    grouped_items.sort(key=lambda row: _grouped_gallery_sort_key(row, filters["sort"], type_sort_lookup))
    total_count = len(grouped_items)
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    offset = (normalized_page - 1) * normalized_page_size
    results = [row["payload"] for row in grouped_items[offset : offset + normalized_page_size]]
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
    item_id: str,
    label: str,
    name: str,
    mana_value: int | None,
    updated_at: datetime,
    types: list["Type"],
    payload: dict[str, object],
) -> GroupedGalleryItem:
    return {
        "item_id": item_id,
        "label": label,
        "name": name,
        "mana_value": mana_value,
        "updated_at": updated_at,
        "types": types,
        "payload": payload,
    }


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

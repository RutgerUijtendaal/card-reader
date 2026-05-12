from __future__ import annotations

from typing import Any, cast

from django.db.models import Prefetch, QuerySet

from card_reader_core.models import (
    Card,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Keyword,
    Symbol,
    Tag,
    Type,
)
from card_reader_core.search.cards import apply_card_search

from .images import resolve_image_file_path
from .types import CardListRow, LatestCardVersionReparseSource, PaginatedCardList


def list_cards(
    *,
    query: str | None,
    max_confidence: float | None,
    keyword_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    mana_cost: str | None = None,
    template_id: str | None = None,
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    page: int = 1,
    page_size: int = 72,
) -> PaginatedCardList:
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    versions = (
        CardVersion.objects.filter(is_latest=True)
        .select_related("card", "template", "previous_version")
        .prefetch_related(
            "images",
            Prefetch(
                "card_version_keywords",
                queryset=CardVersionKeyword.objects.select_related("keyword").order_by("keyword__label"),
            ),
            Prefetch(
                "card_version_tags",
                queryset=CardVersionTag.objects.select_related("tag").order_by("tag__label"),
            ),
            Prefetch(
                "card_version_symbols",
                queryset=CardVersionSymbol.objects.select_related("symbol").order_by("symbol__label"),
            ),
            Prefetch(
                "card_version_types",
                queryset=CardVersionType.objects.select_related("type").order_by("type__label"),
            ),
        )
        .order_by("-updated_at")
    )
    versions = apply_card_search(versions, query)
    versions = apply_card_filters(
        versions,
        max_confidence=max_confidence,
        mana_cost=mana_cost,
        template_id=template_id,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
    )
    versions = filter_by_links(versions, CardVersionKeyword, "keyword_id", keyword_ids)
    versions = filter_by_links(versions, CardVersionTag, "tag_id", tag_ids)
    versions = filter_by_links(versions, CardVersionSymbol, "symbol_id", symbol_ids)
    versions = filter_by_links(versions, CardVersionType, "type_id", type_ids)

    total_count = versions.count()
    offset = (normalized_page - 1) * normalized_page_size
    version_rows = list(versions[offset : offset + normalized_page_size])
    if not version_rows:
        return PaginatedCardList(
            count=total_count,
            page=normalized_page,
            page_size=normalized_page_size,
            results=[],
        )

    results: list[CardListRow] = []
    for version in version_rows:
        images = cast(Any, version).images.all()
        keywords = cast(Any, version).card_version_keywords.all()
        tags = cast(Any, version).card_version_tags.all()
        symbols = cast(Any, version).card_version_symbols.all()
        types = cast(Any, version).card_version_types.all()
        results.append(
            CardListRow(
                version=version,
                image=next(iter(images), None),
                keywords=[cast(Keyword, row.keyword) for row in keywords],
                tags=[cast(Tag, row.tag) for row in tags],
                symbols=[cast(Symbol, row.symbol) for row in symbols],
                types=[cast(Type, row.type) for row in types],
            )
        )

    return PaginatedCardList(
        count=total_count,
        page=normalized_page,
        page_size=normalized_page_size,
        results=results,
    )


def get_card(card_id: str) -> Card | None:
    return Card.objects.filter(id=card_id).first()


def get_latest_card_version(card_id: str) -> CardVersion | None:
    return (
        CardVersion.objects.filter(card_id=card_id, is_latest=True)
        .select_related("card", "template", "previous_version", "parse_result")
        .order_by("-version_number")
        .first()
    )


def get_card_image(card_version_id: str) -> CardVersionImage | None:
    images = CardVersionImage.objects.filter(card_version_id=card_version_id).order_by("-created_at")
    first_image: CardVersionImage | None = None
    for image in images:
        if first_image is None:
            first_image = image
        if resolve_image_file_path(image) is not None:
            return image
    return first_image


def list_latest_card_version_reparse_sources() -> list[LatestCardVersionReparseSource]:
    versions = [
        card.latest_version
        for card in Card.objects.exclude(latest_version__isnull=True)
        .select_related("latest_version__template")
        .prefetch_related("latest_version__images")
        .order_by("id")
        if card.latest_version is not None
    ]
    if not versions:
        return []

    out: list[LatestCardVersionReparseSource] = []
    for version in versions:
        image = next(iter(cast(Any, version).images.all()), None)
        if image is None:
            continue
        image_path = resolve_image_file_path(image)
        if image_path is None:
            continue
        out.append(
            LatestCardVersionReparseSource(
                card_version_id=version.id,
                template_id=version.template.key,
                image_path=image_path,
            )
        )
    return out


def list_card_generations(card_id: str) -> list[CardVersion]:
    return list(
        CardVersion.objects.filter(card_id=card_id)
        .select_related("card", "template", "previous_version", "parse_result")
        .order_by("-version_number")
    )


def apply_card_filters(queryset: QuerySet[CardVersion], **filters: object) -> QuerySet[CardVersion]:
    if filters["max_confidence"] is not None:
        queryset = queryset.filter(confidence__lte=filters["max_confidence"])
    if filters["mana_cost"]:
        queryset = queryset.filter(mana_cost=filters["mana_cost"])
    if filters["template_id"]:
        queryset = queryset.filter(template_id=filters["template_id"])
    if filters["attack_min"] is not None:
        queryset = queryset.filter(attack__isnull=False, attack__gte=filters["attack_min"])
    if filters["attack_max"] is not None:
        queryset = queryset.filter(attack__isnull=False, attack__lte=filters["attack_max"])
    if filters["health_min"] is not None:
        queryset = queryset.filter(health__isnull=False, health__gte=filters["health_min"])
    if filters["health_max"] is not None:
        queryset = queryset.filter(health__isnull=False, health__lte=filters["health_max"])
    return queryset


def filter_by_links(
    queryset: QuerySet[CardVersion],
    link_model: type[CardVersionKeyword] | type[CardVersionTag] | type[CardVersionSymbol] | type[CardVersionType],
    link_field: str,
    values: list[str] | None,
) -> QuerySet[CardVersion]:
    if not values:
        return queryset
    version_ids = link_model.objects.filter(**{f"{link_field}__in": values}).values_list(
        "card_version_id",
        flat=True,
    )
    return queryset.filter(id__in=version_ids)

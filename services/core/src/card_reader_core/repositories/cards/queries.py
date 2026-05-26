from __future__ import annotations

from django.db.models import Case, CharField, Count, Exists, F, IntegerField, OuterRef, Prefetch, Q, QuerySet, Subquery, Value, When

from card_reader_core.models import (
    Card,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Type,
)
from card_reader_core.search.cards import apply_card_search

from .images import resolve_image_file_path
from .types import (
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_TYPES_ASC,
    CARD_SORT_UPDATED_DESC,
    DEFAULT_CARD_PAGE_SIZE,
    CardListRow,
    CardSort,
    LatestCardVersionReparseSource,
    PaginatedCardList,
)

MANA_TYPE_KEY = "mana"


def list_cards(
    *,
    query: str | None,
    max_confidence: float | None,
    card_ids: list[str] | None = None,
    keyword_ids: list[str] | None = None,
    keyword_match: str | None = None,
    tag_ids: list[str] | None = None,
    tag_match: str | None = None,
    mana_symbol_ids: list[str] | None = None,
    mana_symbol_match: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    devotion_symbol_ids: list[str] | None = None,
    devotion_symbol_match: str | None = None,
    other_symbol_ids: list[str] | None = None,
    other_symbol_match: str | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    type_match: str | None = None,
    mana_cost_min: int | None = None,
    mana_cost_max: int | None = None,
    template_id: str | None = None,
    is_hero: bool | None = None,
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    sort: CardSort = CARD_SORT_UPDATED_DESC,
    page: int = 1,
    page_size: int = DEFAULT_CARD_PAGE_SIZE,
) -> PaginatedCardList:
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    versions = _build_filtered_versions_queryset(
        query=query,
        card_ids=card_ids,
        max_confidence=max_confidence,
        keyword_ids=keyword_ids,
        keyword_match=keyword_match,
        tag_ids=tag_ids,
        tag_match=tag_match,
        mana_symbol_ids=mana_symbol_ids,
        mana_symbol_match=mana_symbol_match,
        affinity_symbol_ids=affinity_symbol_ids,
        affinity_symbol_match=affinity_symbol_match,
        devotion_symbol_ids=devotion_symbol_ids,
        devotion_symbol_match=devotion_symbol_match,
        other_symbol_ids=other_symbol_ids,
        other_symbol_match=other_symbol_match,
        symbol_ids=symbol_ids,
        type_ids=type_ids,
        type_match=type_match,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        is_hero=is_hero,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        sort=sort,
    )

    total_count = versions.count()
    offset = (normalized_page - 1) * normalized_page_size
    results = _build_card_list_rows(list(versions[offset : offset + normalized_page_size]))
    if not results:
        return PaginatedCardList(
            count=total_count,
            page=normalized_page,
            page_size=normalized_page_size,
            results=[],
        )

    return PaginatedCardList(
        count=total_count,
        page=normalized_page,
        page_size=normalized_page_size,
        results=results,
    )


def list_matching_cards(
    *,
    query: str | None,
    max_confidence: float | None,
    card_ids: list[str] | None = None,
    keyword_ids: list[str] | None = None,
    keyword_match: str | None = None,
    tag_ids: list[str] | None = None,
    tag_match: str | None = None,
    mana_symbol_ids: list[str] | None = None,
    mana_symbol_match: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    devotion_symbol_ids: list[str] | None = None,
    devotion_symbol_match: str | None = None,
    other_symbol_ids: list[str] | None = None,
    other_symbol_match: str | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    type_match: str | None = None,
    mana_cost_min: int | None = None,
    mana_cost_max: int | None = None,
    template_id: str | None = None,
    is_hero: bool | None = None,
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    sort: CardSort = CARD_SORT_UPDATED_DESC,
) -> list[CardListRow]:
    versions = _build_filtered_versions_queryset(
        query=query,
        card_ids=card_ids,
        max_confidence=max_confidence,
        keyword_ids=keyword_ids,
        keyword_match=keyword_match,
        tag_ids=tag_ids,
        tag_match=tag_match,
        mana_symbol_ids=mana_symbol_ids,
        mana_symbol_match=mana_symbol_match,
        affinity_symbol_ids=affinity_symbol_ids,
        affinity_symbol_match=affinity_symbol_match,
        devotion_symbol_ids=devotion_symbol_ids,
        devotion_symbol_match=devotion_symbol_match,
        other_symbol_ids=other_symbol_ids,
        other_symbol_match=other_symbol_match,
        symbol_ids=symbol_ids,
        type_ids=type_ids,
        type_match=type_match,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        is_hero=is_hero,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        sort=sort,
    )
    return _build_card_list_rows(list(versions))


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
    latest_versions = [
        (card.id, card.latest_version)
        for card in Card.objects.exclude(latest_version__isnull=True)
        .select_related("latest_version__template")
        .prefetch_related("latest_version__images")
        .order_by("id")
        if card.latest_version is not None
    ]
    if not latest_versions:
        return []

    out: list[LatestCardVersionReparseSource] = []
    for card_id, version in latest_versions:
        image = next(iter(version.images.all()), None)
        if image is None:
            continue
        image_path = resolve_image_file_path(image)
        if image_path is None:
            continue
        out.append(
            LatestCardVersionReparseSource(
                card_id=card_id,
                card_version_id=version.id,
                template_id=version.template.key,
                image_path=image_path,
            )
        )
    return out


def list_filtered_latest_card_version_reparse_sources(
    *,
    query: str | None,
    max_confidence: float | None,
    card_ids: list[str] | None = None,
    keyword_ids: list[str] | None = None,
    keyword_match: str | None = None,
    tag_ids: list[str] | None = None,
    tag_match: str | None = None,
    mana_symbol_ids: list[str] | None = None,
    mana_symbol_match: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    devotion_symbol_ids: list[str] | None = None,
    devotion_symbol_match: str | None = None,
    other_symbol_ids: list[str] | None = None,
    other_symbol_match: str | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    type_match: str | None = None,
    mana_cost_min: int | None = None,
    mana_cost_max: int | None = None,
    template_id: str | None = None,
    is_hero: bool | None = None,
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    sort: CardSort = CARD_SORT_UPDATED_DESC,
) -> list[LatestCardVersionReparseSource]:
    versions = _build_filtered_versions_queryset(
        query=query,
        card_ids=card_ids,
        max_confidence=max_confidence,
        keyword_ids=keyword_ids,
        keyword_match=keyword_match,
        tag_ids=tag_ids,
        tag_match=tag_match,
        mana_symbol_ids=mana_symbol_ids,
        mana_symbol_match=mana_symbol_match,
        affinity_symbol_ids=affinity_symbol_ids,
        affinity_symbol_match=affinity_symbol_match,
        devotion_symbol_ids=devotion_symbol_ids,
        devotion_symbol_match=devotion_symbol_match,
        other_symbol_ids=other_symbol_ids,
        other_symbol_match=other_symbol_match,
        symbol_ids=symbol_ids,
        type_ids=type_ids,
        type_match=type_match,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        is_hero=is_hero,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        sort=sort,
    )
    out: list[LatestCardVersionReparseSource] = []
    for version in versions:
        image_path = None
        for image in version.images.all():
            image_path = resolve_image_file_path(image)
            if image_path is not None:
                break
        if image_path is None:
            continue
        out.append(
            LatestCardVersionReparseSource(
                card_id=version.card.id,
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
    if filters["mana_cost_min"] is not None:
        queryset = queryset.filter(mana_value__isnull=False, mana_value__gte=filters["mana_cost_min"])
    if filters["mana_cost_max"] is not None:
        queryset = queryset.filter(mana_value__isnull=False, mana_value__lte=filters["mana_cost_max"])
    if filters["template_id"]:
        queryset = queryset.filter(template__key=filters["template_id"])
    if filters["is_hero"] is not None:
        queryset = queryset.filter(card__is_hero=filters["is_hero"])
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
    *,
    match_mode: str | None = None,
) -> QuerySet[CardVersion]:
    if not values:
        return queryset
    normalized_values = list(dict.fromkeys(values))
    link_rows = link_model.objects.filter(**{f"{link_field}__in": normalized_values})
    if match_mode == "all":
        version_ids = (
            link_rows.values("card_version_id")
            .annotate(match_count=Count(link_field, distinct=True))
            .filter(match_count=len(normalized_values))
            .values_list("card_version_id", flat=True)
        )
    else:
        version_ids = link_rows.values_list("card_version_id", flat=True)
    return queryset.filter(id__in=version_ids)


def _build_filtered_versions_queryset(
    *,
    query: str | None,
    card_ids: list[str] | None,
    max_confidence: float | None,
    keyword_ids: list[str] | None,
    keyword_match: str | None,
    tag_ids: list[str] | None,
    tag_match: str | None,
    mana_symbol_ids: list[str] | None,
    mana_symbol_match: str | None,
    affinity_symbol_ids: list[str] | None,
    affinity_symbol_match: str | None,
    devotion_symbol_ids: list[str] | None,
    devotion_symbol_match: str | None,
    other_symbol_ids: list[str] | None,
    other_symbol_match: str | None,
    symbol_ids: list[str] | None,
    type_ids: list[str] | None,
    type_match: str | None,
    mana_cost_min: int | None,
    mana_cost_max: int | None,
    template_id: str | None,
    is_hero: bool | None,
    attack_min: int | None,
    attack_max: int | None,
    health_min: int | None,
    health_max: int | None,
    sort: CardSort,
) -> QuerySet[CardVersion]:
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
    )
    versions = apply_card_search(versions, query)
    if card_ids:
        versions = versions.filter(card_id__in=list(dict.fromkeys(card_ids)))
    versions = apply_card_filters(
        versions,
        max_confidence=max_confidence,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        is_hero=is_hero,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
    )
    versions = filter_by_links(versions, CardVersionKeyword, "keyword_id", keyword_ids, match_mode=keyword_match)
    versions = filter_by_links(versions, CardVersionTag, "tag_id", tag_ids, match_mode=tag_match)
    versions = filter_by_links(versions, CardVersionSymbol, "symbol_id", mana_symbol_ids, match_mode=mana_symbol_match)
    versions = filter_by_links(
        versions, CardVersionSymbol, "symbol_id", affinity_symbol_ids, match_mode=affinity_symbol_match
    )
    versions = filter_by_links(
        versions, CardVersionSymbol, "symbol_id", devotion_symbol_ids, match_mode=devotion_symbol_match
    )
    versions = filter_by_links(versions, CardVersionSymbol, "symbol_id", other_symbol_ids, match_mode=other_symbol_match)
    versions = filter_by_links(versions, CardVersionSymbol, "symbol_id", symbol_ids)
    versions = filter_by_links(versions, CardVersionType, "type_id", type_ids, match_mode=type_match)
    return _apply_card_sort(versions, sort)


def _apply_card_sort(queryset: QuerySet[CardVersion], sort: CardSort) -> QuerySet[CardVersion]:
    if sort == CARD_SORT_NAME_ASC:
        return queryset.order_by("name", "card__label", "card__id")
    if sort == CARD_SORT_MANA_ASC:
        return queryset.order_by(
            F("mana_value").asc(nulls_last=True),
            "name",
            "card__label",
            "card__id",
        )
    if sort == CARD_SORT_MANA_DESC:
        return queryset.order_by(
            F("mana_value").desc(nulls_last=True),
            "name",
            "card__label",
            "card__id",
        )
    if sort == CARD_SORT_TYPES_ASC:
        global_type_link_counts = (
            Type.objects.filter(pk=OuterRef("type_id"))
            .annotate(
                linked_card_count=Count(
                    "card_version_types",
                    filter=Q(card_version_types__card_version__is_latest=True),
                    distinct=True,
                )
            )
            .values("linked_card_count")[:1]
        )
        best_non_mana_types = (
            CardVersionType.objects.filter(card_version_id=OuterRef("pk"))
            .exclude(type__key__iexact=MANA_TYPE_KEY)
            .annotate(
                type_linked_card_count=Subquery(global_type_link_counts, output_field=IntegerField()),
                type_label=F("type__label"),
            )
            .order_by(F("type_linked_card_count").desc(nulls_last=True), "type_label", "type_id")
        )
        queryset = queryset.annotate(
            has_mana_type=Exists(
                CardVersionType.objects.filter(
                    card_version_id=OuterRef("pk"),
                    type__key__iexact=MANA_TYPE_KEY,
                )
            ),
            primary_type_count=Subquery(
                best_non_mana_types.values("type_linked_card_count")[:1],
                output_field=IntegerField(),
            ),
            primary_type_label=Subquery(
                best_non_mana_types.values("type_label")[:1],
                output_field=CharField(),
            ),
        ).annotate(
            type_sort_bucket=Case(
                When(primary_type_count__isnull=False, then=Value(0)),
                When(has_mana_type=True, then=Value(2)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        return queryset.order_by(
            "type_sort_bucket",
            F("primary_type_count").desc(nulls_last=True),
            F("primary_type_label").asc(nulls_last=True),
            "name",
            "card__label",
            "card__id",
        )
    return queryset.order_by("-updated_at", "card__label", "card__id")


def _build_card_list_rows(version_rows: list[CardVersion]) -> list[CardListRow]:
    results: list[CardListRow] = []
    for version in version_rows:
        images = version.images.all()
        keywords = version.card_version_keywords.all()
        tags = version.card_version_tags.all()
        symbols = version.card_version_symbols.all()
        types = version.card_version_types.all()
        results.append(
            CardListRow(
                version=version,
                image=next(iter(images), None),
                keywords=[row.keyword for row in keywords],
                tags=[row.tag for row in tags],
                symbols=[row.symbol for row in symbols],
                types=[row.type for row in types],
            )
        )
    return results

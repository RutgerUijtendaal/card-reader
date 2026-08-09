from __future__ import annotations

from typing import Any

from django.db.models import Count, F, Prefetch, Q, QuerySet

from card_reader_core.metadata import mana_family_symbol_keys, normalize_mana_family_keys
from card_reader_core.models import (
    DEFAULT_CARD_POOL,
    STANDARD_CARD_ROLE,
    Card,
    CardPool,
    CardRoleAssignment,
    CardRoleFilter,
    CardMergeRedirect,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Type,
    active_card_lifecycle_q,
    filter_queryset_by_card_lifecycle,
)
from card_reader_core.search.cards import apply_card_search

from .images import resolve_image_file_path
from .types import (
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
    CARD_SORT_MANA_TYPE_ASC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_TYPES_ASC,
    CARD_SORT_UPDATED_DESC,
    DEFAULT_CARD_PAGE_SIZE,
    DEFAULT_CARD_LIFECYCLE_FILTER,
    CardListCandidate,
    CardLifecycleFilter,
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
    mana_symbol_exclude_ids: list[str] | None = None,
    mana_symbol_match: str | None = None,
    mana_family_keys: list[str] | None = None,
    mana_family_exclude_keys: list[str] | None = None,
    mana_family_match: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    devotion_symbol_ids: list[str] | None = None,
    devotion_symbol_exclude_ids: list[str] | None = None,
    devotion_symbol_match: str | None = None,
    other_symbol_ids: list[str] | None = None,
    other_symbol_exclude_ids: list[str] | None = None,
    other_symbol_match: str | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    type_exclude_ids: list[str] | None = None,
    type_match: str | None = None,
    mana_cost_min: int | None = None,
    mana_cost_max: int | None = None,
    template_id: str | None = None,
    card_pool: CardPool = DEFAULT_CARD_POOL,
    card_roles: list[CardRoleFilter] | None = None,
    card_role_exclude: list[CardRoleFilter] | None = None,
    card_role_match: str = "any",
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
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
        mana_symbol_exclude_ids=mana_symbol_exclude_ids,
        mana_symbol_match=mana_symbol_match,
        mana_family_keys=mana_family_keys,
        mana_family_exclude_keys=mana_family_exclude_keys,
        mana_family_match=mana_family_match,
        affinity_symbol_ids=affinity_symbol_ids,
        affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
        affinity_symbol_match=affinity_symbol_match,
        devotion_symbol_ids=devotion_symbol_ids,
        devotion_symbol_exclude_ids=devotion_symbol_exclude_ids,
        devotion_symbol_match=devotion_symbol_match,
        other_symbol_ids=other_symbol_ids,
        other_symbol_exclude_ids=other_symbol_exclude_ids,
        other_symbol_match=other_symbol_match,
        symbol_ids=symbol_ids,
        type_ids=type_ids,
        type_exclude_ids=type_exclude_ids,
        type_match=type_match,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        card_pool=card_pool,
        card_roles=card_roles,
        card_role_exclude=card_role_exclude,
        card_role_match=card_role_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        lifecycle_status=lifecycle_status,
    )

    offset = (normalized_page - 1) * normalized_page_size
    total_count, page_ids = _paginated_card_version_ids(
        versions,
        sort=sort,
        offset=offset,
        limit=normalized_page_size,
    )
    results = get_card_list_rows_by_version_ids(page_ids)

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
    mana_symbol_exclude_ids: list[str] | None = None,
    mana_symbol_match: str | None = None,
    mana_family_keys: list[str] | None = None,
    mana_family_exclude_keys: list[str] | None = None,
    mana_family_match: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    devotion_symbol_ids: list[str] | None = None,
    devotion_symbol_exclude_ids: list[str] | None = None,
    devotion_symbol_match: str | None = None,
    other_symbol_ids: list[str] | None = None,
    other_symbol_exclude_ids: list[str] | None = None,
    other_symbol_match: str | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    type_exclude_ids: list[str] | None = None,
    type_match: str | None = None,
    mana_cost_min: int | None = None,
    mana_cost_max: int | None = None,
    template_id: str | None = None,
    card_pool: CardPool = DEFAULT_CARD_POOL,
    card_roles: list[CardRoleFilter] | None = None,
    card_role_exclude: list[CardRoleFilter] | None = None,
    card_role_match: str = "any",
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
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
        mana_symbol_exclude_ids=mana_symbol_exclude_ids,
        mana_symbol_match=mana_symbol_match,
        mana_family_keys=mana_family_keys,
        mana_family_exclude_keys=mana_family_exclude_keys,
        mana_family_match=mana_family_match,
        affinity_symbol_ids=affinity_symbol_ids,
        affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
        affinity_symbol_match=affinity_symbol_match,
        devotion_symbol_ids=devotion_symbol_ids,
        devotion_symbol_exclude_ids=devotion_symbol_exclude_ids,
        devotion_symbol_match=devotion_symbol_match,
        other_symbol_ids=other_symbol_ids,
        other_symbol_exclude_ids=other_symbol_exclude_ids,
        other_symbol_match=other_symbol_match,
        symbol_ids=symbol_ids,
        type_ids=type_ids,
        type_exclude_ids=type_exclude_ids,
        type_match=type_match,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        card_pool=card_pool,
        card_roles=card_roles,
        card_role_exclude=card_role_exclude,
        card_role_match=card_role_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        lifecycle_status=lifecycle_status,
    )
    version_ids = _ordered_card_version_ids(versions, sort)
    return get_card_list_rows_by_version_ids(version_ids)


def list_matching_card_candidates(
    *,
    query: str | None,
    max_confidence: float | None,
    card_ids: list[str] | None = None,
    keyword_ids: list[str] | None = None,
    keyword_match: str | None = None,
    tag_ids: list[str] | None = None,
    tag_match: str | None = None,
    mana_symbol_ids: list[str] | None = None,
    mana_symbol_exclude_ids: list[str] | None = None,
    mana_symbol_match: str | None = None,
    mana_family_keys: list[str] | None = None,
    mana_family_exclude_keys: list[str] | None = None,
    mana_family_match: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    devotion_symbol_ids: list[str] | None = None,
    devotion_symbol_exclude_ids: list[str] | None = None,
    devotion_symbol_match: str | None = None,
    other_symbol_ids: list[str] | None = None,
    other_symbol_exclude_ids: list[str] | None = None,
    other_symbol_match: str | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    type_exclude_ids: list[str] | None = None,
    type_match: str | None = None,
    mana_cost_min: int | None = None,
    mana_cost_max: int | None = None,
    template_id: str | None = None,
    card_pool: CardPool = DEFAULT_CARD_POOL,
    card_roles: list[CardRoleFilter] | None = None,
    card_role_exclude: list[CardRoleFilter] | None = None,
    card_role_match: str = "any",
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    sort: CardSort = CARD_SORT_UPDATED_DESC,
) -> list[CardListCandidate]:
    versions = _build_filtered_versions_queryset(
        query=query,
        card_ids=card_ids,
        max_confidence=max_confidence,
        keyword_ids=keyword_ids,
        keyword_match=keyword_match,
        tag_ids=tag_ids,
        tag_match=tag_match,
        mana_symbol_ids=mana_symbol_ids,
        mana_symbol_exclude_ids=mana_symbol_exclude_ids,
        mana_symbol_match=mana_symbol_match,
        mana_family_keys=mana_family_keys,
        mana_family_exclude_keys=mana_family_exclude_keys,
        mana_family_match=mana_family_match,
        affinity_symbol_ids=affinity_symbol_ids,
        affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
        affinity_symbol_match=affinity_symbol_match,
        devotion_symbol_ids=devotion_symbol_ids,
        devotion_symbol_exclude_ids=devotion_symbol_exclude_ids,
        devotion_symbol_match=devotion_symbol_match,
        other_symbol_ids=other_symbol_ids,
        other_symbol_exclude_ids=other_symbol_exclude_ids,
        other_symbol_match=other_symbol_match,
        symbol_ids=symbol_ids,
        type_ids=type_ids,
        type_exclude_ids=type_exclude_ids,
        type_match=type_match,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        card_pool=card_pool,
        card_roles=card_roles,
        card_role_exclude=card_role_exclude,
        card_role_match=card_role_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        lifecycle_status=lifecycle_status,
    )
    version_ids = _ordered_card_version_ids(versions, sort)
    return _hydrate_card_list_candidates(
        version_ids,
        include_types=sort == CARD_SORT_TYPES_ASC,
    )


def get_card(card_id: str) -> Card | None:
    card = Card.objects.prefetch_related("role_assignments").filter(id=card_id).first()
    if card is not None:
        return card
    redirect = (
        CardMergeRedirect.objects.select_related("target_card")
        .prefetch_related("target_card__role_assignments")
        .filter(old_card_id=card_id)
        .first()
    )
    return redirect.target_card if redirect is not None else None


def get_latest_card_version(card_id: str) -> CardVersion | None:
    return (
        CardVersion.objects.filter(card_id=card_id, is_latest=True)
        .select_related("card", "template", "previous_version", "parse_result", "content_version")
        .prefetch_related("card__role_assignments")
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
        .filter(active_card_lifecycle_q(field_path="lifecycle_status"))
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
    mana_symbol_exclude_ids: list[str] | None = None,
    mana_symbol_match: str | None = None,
    mana_family_keys: list[str] | None = None,
    mana_family_exclude_keys: list[str] | None = None,
    mana_family_match: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    devotion_symbol_ids: list[str] | None = None,
    devotion_symbol_exclude_ids: list[str] | None = None,
    devotion_symbol_match: str | None = None,
    other_symbol_ids: list[str] | None = None,
    other_symbol_exclude_ids: list[str] | None = None,
    other_symbol_match: str | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    type_exclude_ids: list[str] | None = None,
    type_match: str | None = None,
    mana_cost_min: int | None = None,
    mana_cost_max: int | None = None,
    template_id: str | None = None,
    card_pool: CardPool = DEFAULT_CARD_POOL,
    card_roles: list[CardRoleFilter] | None = None,
    card_role_exclude: list[CardRoleFilter] | None = None,
    card_role_match: str = "any",
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
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
        mana_symbol_exclude_ids=mana_symbol_exclude_ids,
        mana_symbol_match=mana_symbol_match,
        mana_family_keys=mana_family_keys,
        mana_family_exclude_keys=mana_family_exclude_keys,
        mana_family_match=mana_family_match,
        affinity_symbol_ids=affinity_symbol_ids,
        affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
        affinity_symbol_match=affinity_symbol_match,
        devotion_symbol_ids=devotion_symbol_ids,
        devotion_symbol_exclude_ids=devotion_symbol_exclude_ids,
        devotion_symbol_match=devotion_symbol_match,
        other_symbol_ids=other_symbol_ids,
        other_symbol_exclude_ids=other_symbol_exclude_ids,
        other_symbol_match=other_symbol_match,
        symbol_ids=symbol_ids,
        type_ids=type_ids,
        type_exclude_ids=type_exclude_ids,
        type_match=type_match,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        card_pool=card_pool,
        card_roles=card_roles,
        card_role_exclude=card_role_exclude,
        card_role_match=card_role_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        lifecycle_status=lifecycle_status,
    )
    version_ids = _ordered_card_version_ids(versions, sort)
    out: list[LatestCardVersionReparseSource] = []
    for version in _hydrate_card_versions(version_ids):
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
    card = get_card(card_id)
    if card is None:
        return []
    return list(
        CardVersion.objects.filter(card_id=card.id)
        .select_related("card", "template", "previous_version", "parse_result", "content_version")
        .prefetch_related("card__role_assignments")
        .order_by("-version_number")
    )


def list_cards_for_content_version(
    content_version_id: str,
    *,
    lifecycle_status: CardLifecycleFilter = "all",
) -> list[CardListRow]:
    versions = CardVersion.objects.filter(content_version_id=content_version_id)
    versions = filter_queryset_by_card_lifecycle(versions, lifecycle_status)
    versions = (
        versions
        .select_related("card", "template", "previous_version", "content_version")
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
        .order_by("name", "card__label", "card__id", "-version_number")
    )
    return _build_card_list_rows(list(versions))


def apply_card_filters(queryset: QuerySet[CardVersion], **filters: object) -> QuerySet[CardVersion]:
    if filters["max_confidence"] is not None:
        queryset = queryset.filter(confidence__lte=filters["max_confidence"])
    if filters["mana_cost_min"] is not None:
        queryset = queryset.filter(mana_value__isnull=False, mana_value__gte=filters["mana_cost_min"])
    if filters["mana_cost_max"] is not None:
        queryset = queryset.filter(mana_value__isnull=False, mana_value__lte=filters["mana_cost_max"])
    if filters["template_id"]:
        queryset = queryset.filter(template__key=filters["template_id"])
    queryset = queryset.filter(card__card_pool=filters["card_pool"])
    queryset = filter_by_card_roles(
        queryset,
        filters["card_roles"],
        match_mode=str(filters["card_role_match"]),
    )
    queryset = exclude_by_card_roles(queryset, filters["card_role_exclude"])
    if filters["attack_min"] is not None:
        queryset = queryset.filter(attack__isnull=False, attack__gte=filters["attack_min"])
    if filters["attack_max"] is not None:
        queryset = queryset.filter(attack__isnull=False, attack__lte=filters["attack_max"])
    if filters["health_min"] is not None:
        queryset = queryset.filter(health__isnull=False, health__gte=filters["health_min"])
    if filters["health_max"] is not None:
        queryset = queryset.filter(health__isnull=False, health__lte=filters["health_max"])
    return queryset


def filter_by_card_roles(
    queryset: QuerySet[CardVersion],
    values: object,
    *,
    match_mode: str,
) -> QuerySet[CardVersion]:
    if not isinstance(values, list) or not values:
        return queryset
    roles = list(dict.fromkeys(str(value) for value in values))
    includes_standard = STANDARD_CARD_ROLE in roles
    persisted_roles = [role for role in roles if role != STANDARD_CARD_ROLE]
    if match_mode == "all":
        if includes_standard:
            return queryset.filter(card__role_assignments__isnull=True)
        matching_cards = (
            CardRoleAssignment.objects.filter(role__in=persisted_roles)
            .values("card_id")
            .annotate(match_count=Count("role", distinct=True))
            .filter(match_count=len(persisted_roles))
            .values_list("card_id", flat=True)
        )
        return queryset.filter(card_id__in=matching_cards)

    role_query = Q(card__role_assignments__role__in=persisted_roles)
    if includes_standard:
        role_query |= Q(card__role_assignments__isnull=True)
    return queryset.filter(role_query).distinct()


def exclude_by_card_roles(queryset: QuerySet[CardVersion], values: object) -> QuerySet[CardVersion]:
    if not isinstance(values, list) or not values:
        return queryset
    roles = list(dict.fromkeys(str(value) for value in values))
    if STANDARD_CARD_ROLE in roles:
        queryset = queryset.exclude(card__role_assignments__isnull=True)
    persisted_roles = [role for role in roles if role != STANDARD_CARD_ROLE]
    if persisted_roles:
        card_ids = CardRoleAssignment.objects.filter(role__in=persisted_roles).values_list("card_id", flat=True)
        queryset = queryset.exclude(card_id__in=card_ids)
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


def exclude_by_links(
    queryset: QuerySet[CardVersion],
    link_model: type[CardVersionKeyword] | type[CardVersionTag] | type[CardVersionSymbol] | type[CardVersionType],
    link_field: str,
    values: list[str] | None,
) -> QuerySet[CardVersion]:
    if not values:
        return queryset
    normalized_values = list(dict.fromkeys(values))
    version_ids = link_model.objects.filter(**{f"{link_field}__in": normalized_values}).values_list("card_version_id", flat=True)
    return queryset.exclude(id__in=version_ids)


def filter_by_mana_families(
    queryset: QuerySet[CardVersion],
    family_keys: list[str] | None,
    *,
    match_mode: str | None,
) -> QuerySet[CardVersion]:
    normalized_keys = normalize_mana_family_keys(family_keys or [])
    if not normalized_keys:
        return queryset
    if match_mode == "all":
        for family_key in normalized_keys:
            version_ids = CardVersionSymbol.objects.filter(
                symbol__key__in=mana_family_symbol_keys([family_key]),
            ).values_list("card_version_id", flat=True)
            queryset = queryset.filter(id__in=version_ids)
        return queryset
    version_ids = CardVersionSymbol.objects.filter(
        symbol__key__in=mana_family_symbol_keys(list(normalized_keys)),
    ).values_list("card_version_id", flat=True)
    return queryset.filter(id__in=version_ids)


def exclude_by_mana_families(
    queryset: QuerySet[CardVersion],
    family_keys: list[str] | None,
) -> QuerySet[CardVersion]:
    normalized_keys = normalize_mana_family_keys(family_keys or [])
    if not normalized_keys:
        return queryset
    version_ids = CardVersionSymbol.objects.filter(
        symbol__key__in=mana_family_symbol_keys(list(normalized_keys)),
    ).values_list("card_version_id", flat=True)
    return queryset.exclude(id__in=version_ids)


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
    mana_symbol_exclude_ids: list[str] | None,
    mana_symbol_match: str | None,
    mana_family_keys: list[str] | None,
    mana_family_exclude_keys: list[str] | None,
    mana_family_match: str | None,
    affinity_symbol_ids: list[str] | None,
    affinity_symbol_exclude_ids: list[str] | None,
    affinity_symbol_match: str | None,
    devotion_symbol_ids: list[str] | None,
    devotion_symbol_exclude_ids: list[str] | None,
    devotion_symbol_match: str | None,
    other_symbol_ids: list[str] | None,
    other_symbol_exclude_ids: list[str] | None,
    other_symbol_match: str | None,
    symbol_ids: list[str] | None,
    type_ids: list[str] | None,
    type_exclude_ids: list[str] | None,
    type_match: str | None,
    mana_cost_min: int | None,
    mana_cost_max: int | None,
    template_id: str | None,
    card_pool: CardPool,
    card_roles: list[CardRoleFilter] | None,
    card_role_exclude: list[CardRoleFilter] | None,
    card_role_match: str,
    attack_min: int | None,
    attack_max: int | None,
    health_min: int | None,
    health_max: int | None,
    lifecycle_status: CardLifecycleFilter,
) -> QuerySet[CardVersion]:
    versions = CardVersion.objects.filter(is_latest=True)
    versions = apply_card_search(versions, query)
    versions = filter_queryset_by_card_lifecycle(versions, lifecycle_status)
    if card_ids:
        versions = versions.filter(card_id__in=list(dict.fromkeys(card_ids)))
    versions = apply_card_filters(
        versions,
        max_confidence=max_confidence,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        card_pool=card_pool,
        card_roles=card_roles,
        card_role_exclude=card_role_exclude,
        card_role_match=card_role_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
    )
    versions = filter_by_links(versions, CardVersionKeyword, "keyword_id", keyword_ids, match_mode=keyword_match)
    versions = filter_by_links(versions, CardVersionTag, "tag_id", tag_ids, match_mode=tag_match)
    versions = filter_by_links(versions, CardVersionSymbol, "symbol_id", mana_symbol_ids, match_mode=mana_symbol_match)
    versions = exclude_by_links(versions, CardVersionSymbol, "symbol_id", mana_symbol_exclude_ids)
    versions = filter_by_mana_families(versions, mana_family_keys, match_mode=mana_family_match)
    versions = exclude_by_mana_families(versions, mana_family_exclude_keys)
    versions = filter_by_links(
        versions, CardVersionSymbol, "symbol_id", affinity_symbol_ids, match_mode=affinity_symbol_match
    )
    versions = exclude_by_links(versions, CardVersionSymbol, "symbol_id", affinity_symbol_exclude_ids)
    versions = filter_by_links(
        versions, CardVersionSymbol, "symbol_id", devotion_symbol_ids, match_mode=devotion_symbol_match
    )
    versions = exclude_by_links(versions, CardVersionSymbol, "symbol_id", devotion_symbol_exclude_ids)
    versions = filter_by_links(versions, CardVersionSymbol, "symbol_id", other_symbol_ids, match_mode=other_symbol_match)
    versions = exclude_by_links(versions, CardVersionSymbol, "symbol_id", other_symbol_exclude_ids)
    versions = filter_by_links(versions, CardVersionSymbol, "symbol_id", symbol_ids)
    versions = filter_by_links(versions, CardVersionType, "type_id", type_ids, match_mode=type_match)
    versions = exclude_by_links(versions, CardVersionType, "type_id", type_exclude_ids)
    return versions


def _paginated_card_version_ids(
    queryset: QuerySet[CardVersion],
    *,
    sort: CardSort,
    offset: int,
    limit: int,
) -> tuple[int, list[str]]:
    if sort == CARD_SORT_TYPES_ASC:
        ordered_ids = _ordered_type_sort_card_version_ids(queryset)
        return len(ordered_ids), ordered_ids[offset : offset + limit]
    total_count = queryset.count()
    page_ids = list(_apply_sql_card_sort(queryset, sort).values_list("id", flat=True)[offset : offset + limit])
    return total_count, page_ids


def _ordered_card_version_ids(queryset: QuerySet[CardVersion], sort: CardSort) -> list[str]:
    if sort == CARD_SORT_TYPES_ASC:
        return _ordered_type_sort_card_version_ids(queryset)
    return list(_apply_sql_card_sort(queryset, sort).values_list("id", flat=True))


def _apply_sql_card_sort(queryset: QuerySet[CardVersion], sort: CardSort) -> QuerySet[CardVersion]:
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
    if sort == CARD_SORT_MANA_TYPE_ASC:
        return queryset.order_by(
            "mana_family_sort_key",
            "name",
            "card__label",
            "card__id",
        )
    return queryset.order_by("-updated_at", "card__label", "card__id")


def _ordered_type_sort_card_version_ids(queryset: QuerySet[CardVersion]) -> list[str]:
    version_rows = list(queryset.select_related("card"))
    version_ids = [version.id for version in version_rows]
    types_by_version_id = _types_by_card_version_ids(version_ids)
    type_sort_lookup = _type_sort_lookup()
    version_rows.sort(
        key=lambda version: (
            *_card_type_sort_key(types_by_version_id.get(version.id, []), type_sort_lookup),
            version.name.casefold(),
            version.card.label.casefold(),
            version.card.id,
        )
    )
    return [version.id for version in version_rows]


def _hydrate_card_versions(card_version_ids: list[str]) -> list[CardVersion]:
    if not card_version_ids:
        return []
    versions_by_id = {
        version.id: version
        for version in CardVersion.objects.filter(id__in=card_version_ids)
        .select_related("card", "template", "previous_version", "content_version")
        .prefetch_related(*_card_list_prefetches())
    }
    return [versions_by_id[version_id] for version_id in card_version_ids if version_id in versions_by_id]


def get_card_list_rows_by_version_ids(card_version_ids: list[str]) -> list[CardListRow]:
    return _build_card_list_rows(_hydrate_card_versions(card_version_ids))


def get_latest_card_list_rows_by_card_ids(
    card_ids: list[str],
    *,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
) -> list[CardListRow]:
    if not card_ids:
        return []
    normalized_card_ids = list(dict.fromkeys(card_ids))
    versions = CardVersion.objects.filter(card_id__in=normalized_card_ids, is_latest=True)
    versions = filter_queryset_by_card_lifecycle(versions, lifecycle_status)
    latest_version_ids_by_card_id = dict(
        versions
        .order_by("card_id", "version_number")
        .values_list("card_id", "id")
    )
    version_ids = [
        str(latest_version_ids_by_card_id[card_id])
        for card_id in normalized_card_ids
        if latest_version_ids_by_card_id.get(card_id) is not None
    ]
    return get_card_list_rows_by_version_ids(version_ids)


def _hydrate_card_list_candidates(
    card_version_ids: list[str],
    *,
    include_types: bool,
) -> list[CardListCandidate]:
    if not card_version_ids:
        return []
    versions_by_id = {
        version.id: version
        for version in CardVersion.objects.filter(id__in=card_version_ids).select_related("card")
    }
    types_by_version_id = _types_by_card_version_ids(card_version_ids) if include_types else {}
    return [
        CardListCandidate(
            version=versions_by_id[version_id],
            types=types_by_version_id.get(version_id, []),
        )
        for version_id in card_version_ids
        if version_id in versions_by_id
    ]


def _card_list_prefetches() -> tuple[Any, ...]:
    return (
        "card__role_assignments",
        Prefetch("images", queryset=CardVersionImage.objects.order_by("-created_at")),
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


def _types_by_card_version_ids(card_version_ids: list[str]) -> dict[str, list[Type]]:
    if not card_version_ids:
        return {}
    grouped: dict[str, list[Type]] = {version_id: [] for version_id in card_version_ids}
    for row in (
        CardVersionType.objects.filter(card_version_id__in=card_version_ids)
        .select_related("type")
        .order_by("type__label")
    ):
        grouped.setdefault(str(getattr(row, "card_version_id")), []).append(row.type)
    return grouped


def _type_sort_lookup() -> dict[str, tuple[int, str]]:
    lookup: dict[str, tuple[int, str]] = {}
    for row in (
        Type.objects.annotate(
            linked_card_count=Count(
                "card_version_types",
                filter=Q(card_version_types__card_version__is_latest=True)
                & active_card_lifecycle_q(
                    field_path="card_version_types__card_version__card__lifecycle_status",
                ),
                distinct=True,
            ),
        )
        .order_by("label")
    ):
        key = str(row.key).strip().casefold()
        lookup[key] = (int(getattr(row, "linked_card_count", 0)), str(row.label).casefold())
    return lookup


def _card_type_sort_key(
    types: list[Type],
    type_sort_lookup: dict[str, tuple[int, str]],
) -> tuple[int, int, str]:
    if not types:
        return (1, 0, "")

    best_value: tuple[int, int, str] | None = None
    for row in types:
        key = str(row.key).strip().casefold()
        label = str(row.label).casefold()
        if key == MANA_TYPE_KEY:
            candidate = (2, 0, "")
        else:
            linked_card_count, ranked_label = type_sort_lookup.get(key, (0, label))
            candidate = (0, -linked_card_count, ranked_label)
        if best_value is None or candidate < best_value:
            best_value = candidate

    return best_value or (1, 0, "")


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

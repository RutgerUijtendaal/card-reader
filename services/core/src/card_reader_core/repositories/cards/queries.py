from __future__ import annotations

from collections.abc import Collection
from typing import Any, cast

from django.db.models import Count, F, Prefetch, Q, QuerySet, Subquery

from card_reader_core.metadata import normalize_mana_family_keys
from card_reader_core.models import (
    DEFAULT_CARD_POOL,
    CARD_POOLS,
    STANDARD_CARD_ROLE,
    Card,
    CardFaction,
    CardFactionAssignment,
    CardGroup,
    CardGroupMember,
    CardPool,
    CardRoleAssignment,
    CardRoleFilter,
    CardMergeRedirect,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardManaFamilyAssignment,
    CardVersionTag,
    CardVersionType,
    Type,
    active_card_lifecycle_q,
    card_lifecycle_filter_q,
    card_role_keys,
    card_faction_keys,
    card_mana_family_keys,
    filter_queryset_by_card_lifecycle,
)
from card_reader_core.search.cards import apply_card_search

from .images import resolve_image_file_path, select_usable_card_image
from .sorting import (
    apply_default_card_group_sort,
    apply_default_card_sort,
    apply_type_card_sort,
    card_default_sort_key,
)
from .types import (
    CARD_SORT_DEFAULT,
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
    CARD_SORT_MANA_TYPE_ASC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_TYPES_ASC,
    CARD_SORT_UPDATED_DESC,
    DEFAULT_CARD_PAGE_SIZE,
    DEFAULT_CARD_LIFECYCLE_FILTER,
    CardListCandidate,
    CardFilterParams,
    CardLifecycleFilter,
    CardListRow,
    CardSort,
    LatestCardVersionReparseSource,
    GroupedCardListReference,
    PaginatedCardList,
    PaginatedGroupedCardList,
)

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
    card_pool: CardPool | None = DEFAULT_CARD_POOL,
    card_roles: list[CardRoleFilter] | None = None,
    card_role_exclude: list[CardRoleFilter] | None = None,
    card_role_match: str = "any",
    card_factions: list[CardFaction] | None = None,
    card_faction_exclude: list[CardFaction] | None = None,
    card_faction_match: str = "any",
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    sort: CardSort = CARD_SORT_DEFAULT,
    page: int = 1,
    page_size: int = DEFAULT_CARD_PAGE_SIZE,
) -> PaginatedCardList:
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
        card_factions=card_factions,
        card_faction_exclude=card_faction_exclude,
        card_faction_match=card_faction_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        lifecycle_status=lifecycle_status,
    )
    return _paginate_card_list_rows(
        versions,
        sort=sort,
        card_pool=card_pool,
        page=page,
        page_size=page_size,
    )


def list_cards_across_pools(
    *,
    query: str | None = None,
    max_confidence: float | None = None,
    template_id: str | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    page: int = 1,
    page_size: int = DEFAULT_CARD_PAGE_SIZE,
) -> PaginatedCardList:
    """List cards across every card pool."""

    versions = _latest_card_versions_queryset(
        card_pools=CARD_POOLS,
        query=query,
        lifecycle_status=lifecycle_status,
    )
    if max_confidence is not None:
        versions = versions.filter(confidence__lte=max_confidence)
    if template_id:
        versions = versions.filter(template__key=template_id)
    return _paginate_card_list_rows(
        versions,
        sort=CARD_SORT_UPDATED_DESC,
        card_pool=None,
        page=page,
        page_size=page_size,
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
    card_pool: CardPool | None = DEFAULT_CARD_POOL,
    card_roles: list[CardRoleFilter] | None = None,
    card_role_exclude: list[CardRoleFilter] | None = None,
    card_role_match: str = "any",
    card_factions: list[CardFaction] | None = None,
    card_faction_exclude: list[CardFaction] | None = None,
    card_faction_match: str = "any",
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    sort: CardSort = CARD_SORT_DEFAULT,
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
        card_factions=card_factions,
        card_faction_exclude=card_faction_exclude,
        card_faction_match=card_faction_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        lifecycle_status=lifecycle_status,
    )
    version_ids = _ordered_card_version_ids(versions, sort, card_pool=card_pool)
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
    card_pool: CardPool | None = DEFAULT_CARD_POOL,
    card_roles: list[CardRoleFilter] | None = None,
    card_role_exclude: list[CardRoleFilter] | None = None,
    card_role_match: str = "any",
    card_factions: list[CardFaction] | None = None,
    card_faction_exclude: list[CardFaction] | None = None,
    card_faction_match: str = "any",
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    sort: CardSort = CARD_SORT_DEFAULT,
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
        card_factions=card_factions,
        card_faction_exclude=card_faction_exclude,
        card_faction_match=card_faction_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        lifecycle_status=lifecycle_status,
    )
    version_ids = _ordered_card_version_ids(versions, sort, card_pool=card_pool)
    return _hydrate_card_list_candidates(
        version_ids,
        include_types=sort == CARD_SORT_TYPES_ASC,
    )


def list_default_grouped_card_references(
    filters: CardFilterParams,
    *,
    page: int,
    page_size: int,
) -> PaginatedGroupedCardList:
    card_pool = filters["card_pool"]
    if card_pool is None:
        raise ValueError("Grouped default sorting requires one explicit card pool.")

    matching_versions = _build_filtered_versions_from_params(filters)
    matching_card_ids = matching_versions.order_by().values("card_id")
    participating_groups = CardGroup.objects.filter(
        anchor_card__card_pool=card_pool,
        anchor_card__latest_version__isnull=False,
        members__card_id__in=Subquery(matching_card_ids),
    ).distinct()
    participating_group_ids = participating_groups.order_by().values("id")
    participant_card_ids = (
        CardGroupMember.objects.filter(
            group_id__in=Subquery(participating_group_ids),
            card__card_pool=card_pool,
        )
        .filter(
            card_lifecycle_filter_q(
                filters["lifecycle_status"],
                field_path="card__lifecycle_status",
            )
        )
        .values("card_id")
    )
    standalone_versions = matching_versions.exclude(
        card_id__in=Subquery(participant_card_ids)
    )

    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    offset = (normalized_page - 1) * normalized_page_size
    candidate_limit = offset + normalized_page_size
    total_count = standalone_versions.count() + participating_groups.count()

    ordered_standalone = apply_default_card_sort(
        standalone_versions,
        card_pool=card_pool,
    )
    standalone_candidates = list(
        ordered_standalone.select_related("card")
        .prefetch_related(
            "card__role_assignments",
            "card__faction_assignments",
        )[:candidate_limit]
    )
    ordered_groups = apply_default_card_group_sort(
        participating_groups,
        card_pool=card_pool,
    )
    group_candidates = list(
        ordered_groups.select_related(
            "anchor_card",
            "anchor_card__latest_version",
        )
        .prefetch_related(
            "anchor_card__role_assignments",
            "anchor_card__faction_assignments",
        )[:candidate_limit]
    )

    sortable_references: list[
        tuple[tuple[object, ...], GroupedCardListReference]
    ] = []
    for version in standalone_candidates:
        item_id = version.card.id
        sortable_references.append(
            (
                (
                    *card_default_sort_key(
                        card_pool=card_pool,
                        card_id=version.card.id,
                        label=version.card.label,
                        name=version.name,
                        mana_family_sort_key=version.card.mana_family_sort_key,
                        mana_value=version.mana_value,
                        card_roles=card_role_keys(version.card),
                        card_factions=card_faction_keys(version.card),
                    ),
                    item_id,
                ),
                GroupedCardListReference(
                    result_type="card",
                    item_id=item_id,
                    card_version_id=version.id,
                    group_id=None,
                ),
            )
        )
    for group in group_candidates:
        anchor_version = group.anchor_card.latest_version
        if anchor_version is None:
            continue
        item_id = group.id
        sortable_references.append(
            (
                (
                    *card_default_sort_key(
                        card_pool=card_pool,
                        card_id=group.anchor_card.id,
                        label=group.anchor_card.label,
                        name=anchor_version.name,
                        mana_family_sort_key=group.anchor_card.mana_family_sort_key,
                        mana_value=anchor_version.mana_value,
                        card_roles=card_role_keys(group.anchor_card),
                        card_factions=card_faction_keys(group.anchor_card),
                    ),
                    item_id,
                ),
                GroupedCardListReference(
                    result_type="card_group",
                    item_id=item_id,
                    card_version_id=None,
                    group_id=group.id,
                ),
            )
        )

    sortable_references.sort(key=lambda row: row[0])
    page_references = [
        reference
        for _sort_key, reference in sortable_references[
            offset : offset + normalized_page_size
        ]
    ]
    return PaginatedGroupedCardList(
        count=total_count,
        page=normalized_page,
        page_size=normalized_page_size,
        results=page_references,
    )


def get_card(card_id: str) -> Card | None:
    return _get_card(card_id)


def _get_card(card_id: str) -> Card | None:
    cards = Card.objects.prefetch_related(
        "role_assignments", "faction_assignments", "mana_family_assignments"
    ).filter(
        id=card_id
    )
    card = cards.first()
    if card is not None:
        return card
    redirects = (
        CardMergeRedirect.objects.select_related("target_card")
        .prefetch_related(
            "target_card__role_assignments",
            "target_card__faction_assignments",
            "target_card__mana_family_assignments",
        )
        .filter(old_card_id=card_id)
    )
    redirect = redirects.first()
    return redirect.target_card if redirect is not None else None


def get_latest_card_version(card_id: str) -> CardVersion | None:
    return (
        CardVersion.objects.filter(card_id=card_id, is_latest=True)
        .select_related("card", "template", "previous_version", "parse_result", "content_version")
        .prefetch_related(
            "card__role_assignments",
            "card__faction_assignments",
            "card__mana_family_assignments",
        )
        .order_by("-version_number")
        .first()
    )


def get_card_image(card_version_id: str) -> CardVersionImage | None:
    images = CardVersionImage.objects.filter(card_version_id=card_version_id).order_by(
        "-created_at"
    )
    return select_usable_card_image(images)


def list_latest_card_version_reparse_sources() -> list[LatestCardVersionReparseSource]:
    latest_versions = [
        (card, card.latest_version)
        for card in Card.objects.exclude(latest_version__isnull=True)
        .filter(active_card_lifecycle_q(field_path="lifecycle_status"))
        .select_related("latest_version__template")
        .prefetch_related(
            "role_assignments",
            "faction_assignments",
            "mana_family_assignments",
            "latest_version__images",
        )
        .order_by("id")
        if card.latest_version is not None
    ]
    if not latest_versions:
        return []

    out: list[LatestCardVersionReparseSource] = []
    for card, version in latest_versions:
        image = next(iter(version.images.all()), None)
        if image is None:
            continue
        image_path = resolve_image_file_path(image)
        if image_path is None:
            continue
        out.append(
            LatestCardVersionReparseSource(
                card_id=card.id,
                card_version_id=version.id,
                template_id=version.template.key,
                image_path=image_path,
                card_pool=cast(CardPool, card.card_pool),
                card_roles=card_role_keys(card),
                card_factions=card_faction_keys(card),
                card_mana_families=card_mana_family_keys(card),
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
    card_pool: CardPool | None = DEFAULT_CARD_POOL,
    card_roles: list[CardRoleFilter] | None = None,
    card_role_exclude: list[CardRoleFilter] | None = None,
    card_role_match: str = "any",
    card_factions: list[CardFaction] | None = None,
    card_faction_exclude: list[CardFaction] | None = None,
    card_faction_match: str = "any",
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    sort: CardSort = CARD_SORT_DEFAULT,
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
        card_factions=card_factions,
        card_faction_exclude=card_faction_exclude,
        card_faction_match=card_faction_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
        lifecycle_status=lifecycle_status,
    )
    version_ids = _ordered_card_version_ids(versions, sort, card_pool=card_pool)
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
                card_pool=cast(CardPool, version.card.card_pool),
                card_roles=card_role_keys(version.card),
                card_factions=card_faction_keys(version.card),
                card_mana_families=card_mana_family_keys(version.card),
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
        .prefetch_related(
            "card__role_assignments",
            "card__faction_assignments",
            "card__mana_family_assignments",
        )
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
        versions.select_related("card", "template", "previous_version", "content_version")
        .prefetch_related(
            "card__role_assignments",
            "card__faction_assignments",
            "card__mana_family_assignments",
            "images",
            Prefetch(
                "card_version_keywords",
                queryset=CardVersionKeyword.objects.select_related("keyword").order_by(
                    "keyword__label"
                ),
            ),
            Prefetch(
                "card_version_tags",
                queryset=CardVersionTag.objects.select_related("tag").order_by("tag__label"),
            ),
            Prefetch(
                "card_version_symbols",
                queryset=CardVersionSymbol.objects.select_related("symbol").order_by(
                    "symbol__label"
                ),
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
        queryset = queryset.filter(
            mana_value__isnull=False, mana_value__gte=filters["mana_cost_min"]
        )
    if filters["mana_cost_max"] is not None:
        queryset = queryset.filter(
            mana_value__isnull=False, mana_value__lte=filters["mana_cost_max"]
        )
    if filters["template_id"]:
        queryset = queryset.filter(template__key=filters["template_id"])
    queryset = filter_by_card_roles(
        queryset,
        filters["card_roles"],
        match_mode=str(filters["card_role_match"]),
    )
    queryset = exclude_by_card_roles(queryset, filters["card_role_exclude"])
    queryset = filter_by_card_factions(
        queryset,
        filters["card_factions"],
        match_mode=str(filters["card_faction_match"]),
    )
    queryset = exclude_by_card_factions(queryset, filters["card_faction_exclude"])
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
            if persisted_roles:
                return queryset.none()
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
        card_ids = CardRoleAssignment.objects.filter(role__in=persisted_roles).values_list(
            "card_id", flat=True
        )
        queryset = queryset.exclude(card_id__in=card_ids)
    return queryset


def filter_by_card_factions(
    queryset: QuerySet[CardVersion],
    values: object,
    *,
    match_mode: str,
) -> QuerySet[CardVersion]:
    if not isinstance(values, list) or not values:
        return queryset
    factions = list(dict.fromkeys(str(value) for value in values))
    if match_mode == "all":
        matching_cards = (
            CardFactionAssignment.objects.filter(faction__in=factions)
            .values("card_id")
            .annotate(match_count=Count("faction", distinct=True))
            .filter(match_count=len(factions))
            .values_list("card_id", flat=True)
        )
        return queryset.filter(card_id__in=matching_cards)
    return queryset.filter(card__faction_assignments__faction__in=factions).distinct()


def exclude_by_card_factions(
    queryset: QuerySet[CardVersion], values: object
) -> QuerySet[CardVersion]:
    if not isinstance(values, list) or not values:
        return queryset
    card_ids = CardFactionAssignment.objects.filter(faction__in=values).values_list(
        "card_id", flat=True
    )
    return queryset.exclude(card_id__in=card_ids)


def filter_by_links(
    queryset: QuerySet[CardVersion],
    link_model: type[CardVersionKeyword]
    | type[CardVersionTag]
    | type[CardVersionSymbol]
    | type[CardVersionType],
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
    link_model: type[CardVersionKeyword]
    | type[CardVersionTag]
    | type[CardVersionSymbol]
    | type[CardVersionType],
    link_field: str,
    values: list[str] | None,
) -> QuerySet[CardVersion]:
    if not values:
        return queryset
    normalized_values = list(dict.fromkeys(values))
    version_ids = link_model.objects.filter(**{f"{link_field}__in": normalized_values}).values_list(
        "card_version_id", flat=True
    )
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
            queryset = queryset.filter(
                card__mana_family_assignments__mana_family=family_key
            )
        return queryset.distinct()
    return queryset.filter(
        card__mana_family_assignments__mana_family__in=normalized_keys
    ).distinct()


def exclude_by_mana_families(
    queryset: QuerySet[CardVersion],
    family_keys: list[str] | None,
) -> QuerySet[CardVersion]:
    normalized_keys = normalize_mana_family_keys(family_keys or [])
    if not normalized_keys:
        return queryset
    card_ids = CardManaFamilyAssignment.objects.filter(
        mana_family__in=normalized_keys
    ).values_list("card_id", flat=True)
    return queryset.exclude(card_id__in=card_ids)


def _build_filtered_versions_from_params(
    filters: CardFilterParams,
) -> QuerySet[CardVersion]:
    return _build_filtered_versions_queryset(
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
        mana_family_keys=filters["mana_family_keys"],
        mana_family_exclude_keys=filters["mana_family_exclude_keys"],
        mana_family_match=filters["mana_family_match"],
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
        type_exclude_ids=filters["type_exclude_ids"],
        type_match=filters["type_match"],
        mana_cost_min=filters["mana_cost_min"],
        mana_cost_max=filters["mana_cost_max"],
        template_id=filters["template_id"],
        card_pool=filters["card_pool"],
        card_roles=filters["card_roles"],
        card_role_exclude=filters["card_role_exclude"],
        card_role_match=filters["card_role_match"],
        card_factions=filters["card_factions"],
        card_faction_exclude=filters["card_faction_exclude"],
        card_faction_match=filters["card_faction_match"],
        attack_min=filters["attack_min"],
        attack_max=filters["attack_max"],
        health_min=filters["health_min"],
        health_max=filters["health_max"],
        lifecycle_status=filters["lifecycle_status"],
    )


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
    card_pool: CardPool | None,
    card_roles: list[CardRoleFilter] | None,
    card_role_exclude: list[CardRoleFilter] | None,
    card_role_match: str,
    card_factions: list[CardFaction] | None,
    card_faction_exclude: list[CardFaction] | None,
    card_faction_match: str,
    attack_min: int | None,
    attack_max: int | None,
    health_min: int | None,
    health_max: int | None,
    lifecycle_status: CardLifecycleFilter,
) -> QuerySet[CardVersion]:
    versions = _latest_card_versions_queryset(
        card_pools=CARD_POOLS if card_pool is None else (card_pool,),
        query=query,
        lifecycle_status=lifecycle_status,
    )
    if card_ids:
        versions = versions.filter(card_id__in=list(dict.fromkeys(card_ids)))
    versions = apply_card_filters(
        versions,
        max_confidence=max_confidence,
        mana_cost_min=mana_cost_min,
        mana_cost_max=mana_cost_max,
        template_id=template_id,
        card_roles=card_roles,
        card_role_exclude=card_role_exclude,
        card_role_match=card_role_match,
        card_factions=card_factions,
        card_faction_exclude=card_faction_exclude,
        card_faction_match=card_faction_match,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
    )
    versions = filter_by_links(
        versions, CardVersionKeyword, "keyword_id", keyword_ids, match_mode=keyword_match
    )
    versions = filter_by_links(versions, CardVersionTag, "tag_id", tag_ids, match_mode=tag_match)
    versions = filter_by_links(
        versions, CardVersionSymbol, "symbol_id", mana_symbol_ids, match_mode=mana_symbol_match
    )
    versions = exclude_by_links(versions, CardVersionSymbol, "symbol_id", mana_symbol_exclude_ids)
    versions = filter_by_mana_families(versions, mana_family_keys, match_mode=mana_family_match)
    versions = exclude_by_mana_families(versions, mana_family_exclude_keys)
    versions = filter_by_links(
        versions,
        CardVersionSymbol,
        "symbol_id",
        affinity_symbol_ids,
        match_mode=affinity_symbol_match,
    )
    versions = exclude_by_links(
        versions, CardVersionSymbol, "symbol_id", affinity_symbol_exclude_ids
    )
    versions = filter_by_links(
        versions,
        CardVersionSymbol,
        "symbol_id",
        devotion_symbol_ids,
        match_mode=devotion_symbol_match,
    )
    versions = exclude_by_links(
        versions, CardVersionSymbol, "symbol_id", devotion_symbol_exclude_ids
    )
    versions = filter_by_links(
        versions, CardVersionSymbol, "symbol_id", other_symbol_ids, match_mode=other_symbol_match
    )
    versions = exclude_by_links(versions, CardVersionSymbol, "symbol_id", other_symbol_exclude_ids)
    versions = filter_by_links(versions, CardVersionSymbol, "symbol_id", symbol_ids)
    versions = filter_by_links(
        versions, CardVersionType, "type_id", type_ids, match_mode=type_match
    )
    versions = exclude_by_links(versions, CardVersionType, "type_id", type_exclude_ids)
    return versions


def _latest_card_versions_queryset(
    *,
    card_pools: Collection[CardPool],
    query: str | None,
    lifecycle_status: CardLifecycleFilter,
) -> QuerySet[CardVersion]:
    versions = CardVersion.objects.filter(
        is_latest=True,
        card__card_pool__in=tuple(card_pools),
    )
    versions = apply_card_search(versions, query)
    return filter_queryset_by_card_lifecycle(versions, lifecycle_status)


def _paginate_card_list_rows(
    queryset: QuerySet[CardVersion],
    *,
    sort: CardSort,
    card_pool: CardPool | None,
    page: int,
    page_size: int,
) -> PaginatedCardList:
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    offset = (normalized_page - 1) * normalized_page_size
    total_count, page_ids = _paginated_card_version_ids(
        queryset,
        sort=sort,
        card_pool=card_pool,
        offset=offset,
        limit=normalized_page_size,
    )
    return PaginatedCardList(
        count=total_count,
        page=normalized_page,
        page_size=normalized_page_size,
        results=get_card_list_rows_by_version_ids(page_ids),
    )


def _paginated_card_version_ids(
    queryset: QuerySet[CardVersion],
    *,
    sort: CardSort,
    card_pool: CardPool | None,
    offset: int,
    limit: int,
) -> tuple[int, list[str]]:
    total_count = queryset.count()
    page_ids = list(
        _apply_sql_card_sort(queryset, sort, card_pool=card_pool).values_list("id", flat=True)[
            offset : offset + limit
        ]
    )
    return total_count, page_ids


def _ordered_card_version_ids(
    queryset: QuerySet[CardVersion],
    sort: CardSort,
    *,
    card_pool: CardPool | None,
) -> list[str]:
    return list(
        _apply_sql_card_sort(queryset, sort, card_pool=card_pool).values_list("id", flat=True)
    )


def _apply_sql_card_sort(
    queryset: QuerySet[CardVersion],
    sort: CardSort,
    *,
    card_pool: CardPool | None = None,
) -> QuerySet[CardVersion]:
    if sort == CARD_SORT_DEFAULT:
        if card_pool is None:
            raise ValueError("Default sorting requires one explicit card pool.")
        return apply_default_card_sort(queryset, card_pool=card_pool)
    if sort == CARD_SORT_TYPES_ASC:
        if card_pool is None:
            raise ValueError("Type sorting requires one explicit card pool.")
        return apply_type_card_sort(queryset, card_pool=card_pool)
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
            "card__mana_family_sort_key",
            "name",
            "card__label",
            "card__id",
        )
    return queryset.order_by("-updated_at", "card__label", "card__id")


def _hydrate_card_versions(card_version_ids: list[str]) -> list[CardVersion]:
    if not card_version_ids:
        return []
    versions_by_id = {
        version.id: version
        for version in CardVersion.objects.filter(id__in=card_version_ids)
        .select_related("card", "template", "previous_version", "content_version")
        .prefetch_related(*_card_list_prefetches())
    }
    return [
        versions_by_id[version_id]
        for version_id in card_version_ids
        if version_id in versions_by_id
    ]


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
        versions.order_by("card_id", "version_number").values_list("card_id", "id")
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
        for version in CardVersion.objects.filter(id__in=card_version_ids)
        .select_related("card")
        .prefetch_related(
            "card__role_assignments",
            "card__faction_assignments",
            "card__mana_family_assignments",
        )
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
        "card__faction_assignments",
        "card__mana_family_assignments",
        Prefetch("images", queryset=CardVersionImage.objects.order_by("-created_at")),
        Prefetch(
            "card_version_keywords",
            queryset=CardVersionKeyword.objects.select_related("keyword").order_by(
                "keyword__label"
            ),
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

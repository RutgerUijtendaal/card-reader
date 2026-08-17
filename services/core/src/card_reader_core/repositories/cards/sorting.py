from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

from django.db.models import (
    Case,
    F,
    IntegerField,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Lower
from django.db.models.expressions import Combinable
from django.db.models.base import Model

from card_reader_core.models import (
    BLOOD_CARD_FACTION,
    BOON_CARD_ROLE,
    BOSS_CARD_ROLE,
    DARK_CARD_FACTION,
    DIRECTIVE_CARD_ROLE,
    EVENT_CARD_ROLE,
    EVIL_CARD_POOL,
    HERO_CARD_ROLE,
    LOCATION_CARD_ROLE,
    MANA_CARD_ROLE,
    METAL_CARD_FACTION,
    NEUTRAL_CARD_POOL,
    ORDER_CARD_FACTION,
    PLAYER_CARD_POOL,
    REMINDER_CARD_ROLE,
    SHOP_ITEM_CARD_ROLE,
    STANDARD_CARD_ROLE,
    CardFaction,
    CardFactionAssignment,
    CardGroup,
    CardPool,
    CardRole,
    CardRoleFilter,
    CardRoleAssignment,
    CardVersion,
    CardVersionType,
    Type,
)
from card_reader_core.repositories.metadata import list_types_for_card_sort

MANA_TYPE_KEY = "mana"
EVIL_FACTION_SORT_ORDER: tuple[CardFaction, ...] = (
    ORDER_CARD_FACTION,
    BLOOD_CARD_FACTION,
    DARK_CARD_FACTION,
    METAL_CARD_FACTION,
)
DEFAULT_ROLE_SORT_ORDER: tuple[CardRoleFilter, ...] = (
    STANDARD_CARD_ROLE,
    HERO_CARD_ROLE,
    BOSS_CARD_ROLE,
    LOCATION_CARD_ROLE,
    BOON_CARD_ROLE,
    EVENT_CARD_ROLE,
    SHOP_ITEM_CARD_ROLE,
    DIRECTIVE_CARD_ROLE,
    REMINDER_CARD_ROLE,
    MANA_CARD_ROLE,
)


@dataclass(frozen=True)
class ManaFamilyDefaultSort:
    pass


@dataclass(frozen=True)
class FactionDefaultSort:
    order: tuple[CardFaction, ...]


@dataclass(frozen=True)
class RoleDefaultSort:
    priority_roles: tuple[CardRole, ...] = ()


@dataclass(frozen=True)
class ManaValueDefaultSort:
    pass


DefaultSortComponent = (
    ManaFamilyDefaultSort | FactionDefaultSort | RoleDefaultSort | ManaValueDefaultSort
)
DEFAULT_SORT_COMPONENTS: dict[CardPool, tuple[DefaultSortComponent, ...]] = {
    PLAYER_CARD_POOL: (
        ManaFamilyDefaultSort(),
        RoleDefaultSort(priority_roles=(HERO_CARD_ROLE,)),
        ManaValueDefaultSort(),
    ),
    EVIL_CARD_POOL: (
        FactionDefaultSort(order=EVIL_FACTION_SORT_ORDER),
        RoleDefaultSort(priority_roles=(BOSS_CARD_ROLE, LOCATION_CARD_ROLE)),
        ManaValueDefaultSort(),
    ),
    NEUTRAL_CARD_POOL: (RoleDefaultSort(),),
}

TypeSortLookup = dict[str, tuple[int, str]]
_SortableModel = TypeVar("_SortableModel", bound=Model)


def build_type_sort_lookup(*, card_pool: CardPool) -> TypeSortLookup:
    return {
        str(row.key).strip().casefold(): (
            int(getattr(row, "linked_card_count", 0)),
            str(row.label).casefold(),
        )
        for row in list_types_for_card_sort(card_pool=card_pool)
    }


def card_type_sort_key(
    types: Sequence[Type],
    type_sort_lookup: TypeSortLookup,
) -> tuple[int, int, str, str]:
    if not types:
        return (1, 0, "", "")

    best_value: tuple[int, int, str, str] | None = None
    for row in types:
        key = str(row.key).strip().casefold()
        label = str(row.label).casefold()
        if key == MANA_TYPE_KEY:
            candidate = (2, 0, "", key)
        else:
            linked_card_count, ranked_label = type_sort_lookup.get(key, (0, label))
            candidate = (0, -linked_card_count, ranked_label, key)
        if best_value is None or candidate < best_value:
            best_value = candidate

    return best_value or (1, 0, "", "")


def card_default_sort_key(
    *,
    card_pool: CardPool,
    card_id: str,
    label: str,
    name: str,
    mana_family_sort_key: int,
    mana_value: int | None,
    card_roles: Sequence[CardRole],
    card_factions: Sequence[CardFaction],
) -> tuple[object, ...]:
    components = DEFAULT_SORT_COMPONENTS.get(card_pool)
    if components is None:
        raise ValueError(f"Unsupported card pool for default sorting: {card_pool}.")

    sort_key: list[object] = []
    for component in components:
        if isinstance(component, ManaFamilyDefaultSort):
            sort_key.append(mana_family_sort_key)
        elif isinstance(component, FactionDefaultSort):
            sort_key.extend(
                (
                    _first_rank(
                        card_factions,
                        component.order,
                        empty_rank=len(component.order),
                    ),
                    _membership_mask(card_factions, component.order),
                )
            )
        elif isinstance(component, RoleDefaultSort):
            sort_key.extend(_role_sort_key(card_roles, component=component))
        else:
            sort_key.extend((mana_value is None, mana_value if mana_value is not None else 0))
    return (*sort_key, name, label, card_id)


def apply_default_card_sort(
    queryset: QuerySet[CardVersion],
    *,
    card_pool: CardPool,
) -> QuerySet[CardVersion]:
    components = DEFAULT_SORT_COMPONENTS.get(card_pool)
    if components is None:
        raise ValueError(f"Unsupported card pool for default sorting: {card_pool}.")

    annotated = queryset
    ordering: list[str | Combinable] = []
    for component in components:
        if isinstance(component, ManaFamilyDefaultSort):
            ordering.append("card__mana_family_sort_key")
        elif isinstance(component, FactionDefaultSort):
            annotated = _annotate_faction_sort(annotated, component=component)
            ordering.extend(("default_faction_rank", "default_faction_mask"))
        elif isinstance(component, RoleDefaultSort):
            annotated = _annotate_role_sort(annotated, component=component)
            ordering.extend(("default_role_rank", "default_role_mask"))
        else:
            ordering.append(F("mana_value").asc(nulls_last=True))
    return annotated.order_by(*ordering, "name", "card__label", "card__id")


def apply_default_card_group_sort(
    queryset: QuerySet[CardGroup],
    *,
    card_pool: CardPool,
) -> QuerySet[CardGroup]:
    components = DEFAULT_SORT_COMPONENTS.get(card_pool)
    if components is None:
        raise ValueError(f"Unsupported card pool for default sorting: {card_pool}.")

    annotated = queryset
    ordering: list[str | Combinable] = []
    for component in components:
        if isinstance(component, ManaFamilyDefaultSort):
            ordering.append("anchor_card__mana_family_sort_key")
        elif isinstance(component, FactionDefaultSort):
            annotated = _annotate_faction_sort(
                annotated,
                component=component,
                card_id_field="anchor_card_id",
            )
            ordering.extend(("default_faction_rank", "default_faction_mask"))
        elif isinstance(component, RoleDefaultSort):
            annotated = _annotate_role_sort(
                annotated,
                component=component,
                card_id_field="anchor_card_id",
            )
            ordering.extend(("default_role_rank", "default_role_mask"))
        else:
            ordering.append(F("anchor_card__latest_version__mana_value").asc(nulls_last=True))
    return annotated.order_by(
        *ordering,
        "anchor_card__latest_version__name",
        "anchor_card__label",
        "anchor_card__id",
        "id",
    )


def apply_type_card_sort(
    queryset: QuerySet[CardVersion],
    *,
    card_pool: CardPool,
) -> QuerySet[CardVersion]:
    return _annotate_best_type_rank(queryset, card_pool=card_pool).order_by(
        "default_type_rank",
        Lower("name"),
        Lower("card__label"),
        "card__id",
    )


def _annotate_best_type_rank(
    queryset: QuerySet[CardVersion],
    *,
    card_pool: CardPool,
) -> QuerySet[CardVersion]:
    type_rows = list_types_for_card_sort(card_pool=card_pool)
    non_mana_rows = [row for row in type_rows if str(row.key).strip().casefold() != MANA_TYPE_KEY]
    type_rank_by_id = {str(row.id): rank for rank, row in enumerate(non_mana_rows)}
    untyped_rank = len(non_mana_rows)
    for row in type_rows:
        if str(row.key).strip().casefold() == MANA_TYPE_KEY:
            type_rank_by_id[str(row.id)] = untyped_rank + 1

    type_rank_cases = [
        When(type_id=type_id, then=Value(rank)) for type_id, rank in type_rank_by_id.items()
    ]
    best_type_rank = (
        CardVersionType.objects.filter(card_version_id=OuterRef("pk"))
        .annotate(
            default_type_rank=Case(
                *type_rank_cases,
                default=Value(untyped_rank),
                output_field=IntegerField(),
            )
        )
        .order_by("default_type_rank")
        .values("default_type_rank")[:1]
    )
    return queryset.annotate(
        default_type_rank=Coalesce(
            Subquery(best_type_rank, output_field=IntegerField()),
            Value(untyped_rank),
        ),
    )


def _annotate_faction_sort(
    queryset: QuerySet[_SortableModel],
    *,
    component: FactionDefaultSort,
    card_id_field: str = "card_id",
) -> QuerySet[_SortableModel]:
    assignments = CardFactionAssignment.objects.filter(
        card_id=OuterRef(card_id_field)
    )
    rank_query = (
        assignments.annotate(
            sort_rank=Case(
                *[
                    When(faction=faction, then=Value(rank))
                    for rank, faction in enumerate(component.order)
                ],
                default=Value(len(component.order)),
                output_field=IntegerField(),
            )
        )
        .order_by("sort_rank")
        .values("sort_rank")[:1]
    )
    mask_query = (
        assignments.values("card_id")
        .annotate(
            sort_mask=Sum(
                Case(
                    *[
                        When(faction=faction, then=Value(1 << rank))
                        for rank, faction in enumerate(component.order)
                    ],
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )
        .values("sort_mask")[:1]
    )
    return queryset.annotate(
        default_faction_rank=Coalesce(
            Subquery(rank_query, output_field=IntegerField()),
            Value(len(component.order)),
        ),
        default_faction_mask=Coalesce(
            Subquery(mask_query, output_field=IntegerField()),
            Value(0),
        ),
    )


def _annotate_role_sort(
    queryset: QuerySet[_SortableModel],
    *,
    component: RoleDefaultSort,
    card_id_field: str = "card_id",
) -> QuerySet[_SortableModel]:
    role_order = _effective_role_sort_order(component)
    persisted_order = tuple(role for role in role_order if role != STANDARD_CARD_ROLE)
    empty_rank = role_order.index(STANDARD_CARD_ROLE)
    assignments = CardRoleAssignment.objects.filter(card_id=OuterRef(card_id_field))
    rank_query = (
        assignments.annotate(
            sort_rank=Case(
                *[
                    When(role=role, then=Value(role_order.index(role)))
                    for role in persisted_order
                ],
                default=Value(len(role_order)),
                output_field=IntegerField(),
            )
        )
        .order_by("sort_rank")
        .values("sort_rank")[:1]
    )
    mask_query = (
        assignments.values("card_id")
        .annotate(
            sort_mask=Sum(
                Case(
                    *[
                        When(role=role, then=Value(1 << role_order.index(role)))
                        for role in persisted_order
                    ],
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )
        .values("sort_mask")[:1]
    )
    return queryset.annotate(
        default_role_rank=Coalesce(
            Subquery(rank_query, output_field=IntegerField()),
            Value(empty_rank),
        ),
        default_role_mask=Coalesce(
            Subquery(mask_query, output_field=IntegerField()),
            Value(0),
        ),
    )


def _effective_role_sort_order(component: RoleDefaultSort) -> tuple[CardRoleFilter, ...]:
    return (
        *component.priority_roles,
        *(role for role in DEFAULT_ROLE_SORT_ORDER if role not in component.priority_roles),
    )


def _role_sort_key(
    card_roles: Sequence[CardRole],
    *,
    component: RoleDefaultSort,
) -> tuple[int, int]:
    role_order = _effective_role_sort_order(component)
    if not card_roles:
        return (role_order.index(STANDARD_CARD_ROLE), 0)
    return (
        _first_rank(card_roles, role_order, empty_rank=len(role_order)),
        _membership_mask(card_roles, role_order),
    )


def _first_rank[T: str](
    values: Sequence[T],
    order: Sequence[T],
    *,
    empty_rank: int,
) -> int:
    requested = set(values)
    return next((rank for rank, value in enumerate(order) if value in requested), empty_rank)


def _membership_mask[T: str](values: Sequence[T], order: Sequence[T]) -> int:
    requested = set(values)
    return sum(1 << rank for rank, value in enumerate(order) if value in requested)

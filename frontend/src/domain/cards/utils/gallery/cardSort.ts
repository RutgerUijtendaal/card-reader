import type { CardFaction } from '@/domain/cards/cardFactions';
import type { CardPool } from '@/domain/cards/cardPools';
import {
  STANDARD_CARD_ROLE,
  type CardRole,
  type CardRoleFilter,
} from '@/domain/cards/cardRoles';

export type TypeSortMetadata = {
  key: string;
  label: string;
  linked_card_count?: number;
};

export type CardTypeMetadata = {
  key: string;
  label: string;
};

export type CardSort = 'default' | 'updated_desc' | 'name_asc' | 'mana_asc' | 'mana_desc' | 'mana_type_asc' | 'types_asc';

export type CardSortOption = {
  value: CardSort;
  label: string;
  description: string;
};

export const DEFAULT_CARD_SORT: CardSort = 'default';

export const cardSortOptions: CardSortOption[] = [
  {
    value: 'default',
    label: 'Default',
    description: 'Use the natural order for the current card pool.',
  },
  {
    value: 'updated_desc',
    label: 'Recently Updated',
    description: 'Show the most recently updated cards first.',
  },
  {
    value: 'name_asc',
    label: 'Name',
    description: 'Sort cards alphabetically by name.',
  },
  {
    value: 'types_asc',
    label: 'Types',
    description: 'Sort cards by the most prominent linked card type, with Mana last.',
  },
  {
    value: 'mana_asc',
    label: 'Mana Value Low to High',
    description: 'Sort cards by mana value from lowest to highest.',
  },
  {
    value: 'mana_desc',
    label: 'Mana Value High to Low',
    description: 'Sort cards by mana value from highest to lowest.',
  },
  {
    value: 'mana_type_asc',
    label: 'Mana Type',
    description: 'Sort by Arcane, Dark, Divine, Martial, Occult, Primal, multitype, then no mana type.',
  },
];

export const isCardSort = (value: unknown): value is CardSort =>
  typeof value === 'string' && cardSortOptions.some((option) => option.value === value);

export const getCardSortLabel = (sort: CardSort): string =>
  cardSortOptions.find((option) => option.value === sort)?.label ?? 'Default';

export const getCardSortCompactLabel = (sort: CardSort): string => {
  if (sort === 'default') return 'Default';
  if (sort === 'name_asc') return 'Name';
  if (sort === 'mana_asc') return 'Mana ↑';
  if (sort === 'mana_desc') return 'Mana ↓';
  if (sort === 'mana_type_asc') return 'Mana Type';
  if (sort === 'types_asc') return 'Types';
  return 'Updated';
};

export const appendCardSortSearchParam = (params: URLSearchParams, sort: CardSort): URLSearchParams => {
  params.set('sort', sort);
  return params;
};

type SortableCardLike = {
  id: string;
  label: string;
  name: string;
  mana_value: number | null;
  mana_family_sort_key?: number;
  updated_at: string;
  card_roles?: readonly CardRole[];
  card_factions?: readonly CardFaction[];
  types?: CardTypeMetadata[];
};

type TypeSortLookupEntry = {
  linkedCardCount: number;
  label: string;
};

export type TypeSortLookup = Record<string, TypeSortLookupEntry>;
export type CardSortContext = {
  cardPool: CardPool;
  typeSortLookup?: TypeSortLookup;
};
export type TypeSortBucket = {
  key: string;
  normalizedKey: string;
  label: string;
  linkedCardCount: number;
  sortLabel: string;
};

const MANA_TYPE_KEY = 'mana';
const UNTYPED_TYPE_SORT_BUCKET = 1;
const MANA_TYPE_SORT_BUCKET = 2;

export const normalizeTypeKey = (value: string): string => value.trim().toLocaleLowerCase();

export const isManaTypeKey = (value: string): boolean => normalizeTypeKey(value) === MANA_TYPE_KEY;

const parseTimestamp = (value: string): number => {
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
};

const compareStableText = (left: string, right: string): number => {
  if (left === right) return 0;
  return left < right ? -1 : 1;
};

const EVIL_FACTION_SORT_ORDER: readonly CardFaction[] = ['order', 'blood', 'darkness'];
const DEFAULT_ROLE_SORT_ORDER: readonly CardRoleFilter[] = [
  STANDARD_CARD_ROLE,
  'hero',
  'boss',
  'location',
  'boon',
  'event',
  'shop_item',
];

type DefaultSortComponent =
  | { kind: 'manaFamily' }
  | { kind: 'faction'; order: readonly CardFaction[] }
  | { kind: 'role'; priorityRoles: readonly CardRole[] }
  | { kind: 'manaValue' };

const DEFAULT_SORT_COMPONENTS: Record<CardPool, readonly DefaultSortComponent[]> = {
  player: [
    { kind: 'manaFamily' },
    { kind: 'role', priorityRoles: ['hero'] },
    { kind: 'manaValue' },
  ],
  evil: [
    { kind: 'faction', order: EVIL_FACTION_SORT_ORDER },
    { kind: 'role', priorityRoles: ['boss', 'location'] },
    { kind: 'manaValue' },
  ],
  neutral: [
    { kind: 'role', priorityRoles: [] },
  ],
};

export const buildTypeSortBuckets = (types: TypeSortMetadata[]): TypeSortBucket[] =>
  [...types].sort((left, right) => {
    const leftIsMana = isManaTypeKey(left.key);
    const rightIsMana = isManaTypeKey(right.key);
    if (leftIsMana !== rightIsMana) return leftIsMana ? 1 : -1;
    const countDiff = (right.linked_card_count ?? 0) - (left.linked_card_count ?? 0);
    if (countDiff !== 0) return countDiff;
    return left.label.localeCompare(right.label) || left.key.localeCompare(right.key);
  }).map((type) => ({
    key: type.key,
    normalizedKey: normalizeTypeKey(type.key),
    label: type.label,
    linkedCardCount: type.linked_card_count ?? 0,
    sortLabel: type.label.toLocaleLowerCase(),
  }));

export const buildTypeSortLookup = (types: TypeSortMetadata[]): TypeSortLookup => {
  return Object.fromEntries(
    buildTypeSortBuckets(types).map((type) => [
      type.normalizedKey,
      {
        linkedCardCount: type.linkedCardCount,
        label: type.sortLabel,
      },
    ]),
  );
};

const getCardTypeSortValue = (
  card: SortableCardLike,
  typeSortLookup?: TypeSortLookup,
): { bucket: number; linkedCardCount: number; typeLabel: string } => {
  if (!card.types || card.types.length === 0) {
    return {
      bucket: UNTYPED_TYPE_SORT_BUCKET,
      linkedCardCount: 0,
      typeLabel: '',
    };
  }

  let bestValue: { bucket: number; linkedCardCount: number; typeLabel: string } | null = null;
  for (const type of card.types) {
    const normalizedKey = normalizeTypeKey(type.key);
    const fallbackLabel = type.label.toLocaleLowerCase();
    const lookupEntry = typeSortLookup?.[normalizedKey];
    const candidate = isManaTypeKey(normalizedKey)
      ? {
          bucket: MANA_TYPE_SORT_BUCKET,
          linkedCardCount: 0,
          typeLabel: fallbackLabel,
        }
      : {
          bucket: 0,
          linkedCardCount: lookupEntry?.linkedCardCount ?? 0,
          typeLabel: lookupEntry?.label ?? fallbackLabel,
        };
    if (
      bestValue === null
      || candidate.bucket < bestValue.bucket
      || (candidate.bucket === bestValue.bucket && candidate.linkedCardCount > bestValue.linkedCardCount)
      || (
        candidate.bucket === bestValue.bucket
        && candidate.linkedCardCount === bestValue.linkedCardCount
        && candidate.typeLabel.localeCompare(bestValue.typeLabel) < 0
      )
    ) {
      bestValue = candidate;
    }
  }

  return bestValue ?? {
    bucket: UNTYPED_TYPE_SORT_BUCKET,
    linkedCardCount: 0,
    typeLabel: '',
  };
};

const firstClassificationRank = (
  values: readonly string[],
  order: readonly string[],
  emptyRank: number,
): number => {
  const requested = new Set(values);
  const rank = order.findIndex((value) => requested.has(value));
  return rank === -1 ? emptyRank : rank;
};

const classificationMembershipMask = (
  values: readonly string[],
  order: readonly string[],
): number => {
  const requested = new Set(values);
  return order.reduce((mask, value, rank) => (
    requested.has(value) ? mask + (2 ** rank) : mask
  ), 0);
};

const compareCardTypeSort = (
  left: SortableCardLike,
  right: SortableCardLike,
  typeSortLookup?: TypeSortLookup,
): number => {
  const leftType = getCardTypeSortValue(left, typeSortLookup);
  const rightType = getCardTypeSortValue(right, typeSortLookup);
  return leftType.bucket - rightType.bucket
    || rightType.linkedCardCount - leftType.linkedCardCount
    || leftType.typeLabel.localeCompare(rightType.typeLabel);
};

const effectiveRoleSortOrder = (
  priorityRoles: readonly CardRole[],
): readonly CardRoleFilter[] => [
  ...priorityRoles,
  ...DEFAULT_ROLE_SORT_ORDER.filter(
    (role) => role === STANDARD_CARD_ROLE || !priorityRoles.includes(role),
  ),
];

const compareDefaultRoleSort = (
  leftRoles: readonly CardRole[],
  rightRoles: readonly CardRole[],
  priorityRoles: readonly CardRole[],
): number => {
  const order = effectiveRoleSortOrder(priorityRoles);
  const emptyRank = order.indexOf(STANDARD_CARD_ROLE);
  const leftRank = leftRoles.length === 0
    ? emptyRank
    : firstClassificationRank(leftRoles, order, order.length);
  const rightRank = rightRoles.length === 0
    ? emptyRank
    : firstClassificationRank(rightRoles, order, order.length);
  return leftRank - rightRank
    || classificationMembershipMask(leftRoles, order)
    - classificationMembershipMask(rightRoles, order);
};

const compareNullableManaValue = (
  leftMana: number | null,
  rightMana: number | null,
): number => {
  if (leftMana === null && rightMana !== null) return 1;
  if (leftMana !== null && rightMana === null) return -1;
  return leftMana !== null && rightMana !== null ? leftMana - rightMana : 0;
};

const compareDefaultCardSort = (
  left: SortableCardLike,
  right: SortableCardLike,
  context: CardSortContext,
): number => {
  for (const component of DEFAULT_SORT_COMPONENTS[context.cardPool]) {
    let difference = 0;
    if (component.kind === 'manaFamily') {
      difference = (left.mana_family_sort_key ?? Number.MAX_SAFE_INTEGER)
        - (right.mana_family_sort_key ?? Number.MAX_SAFE_INTEGER);
    } else if (component.kind === 'faction') {
      const leftFactions = left.card_factions ?? [];
      const rightFactions = right.card_factions ?? [];
      difference = firstClassificationRank(leftFactions, component.order, component.order.length)
        - firstClassificationRank(rightFactions, component.order, component.order.length)
        || classificationMembershipMask(leftFactions, component.order)
        - classificationMembershipMask(rightFactions, component.order);
    } else if (component.kind === 'role') {
      difference = compareDefaultRoleSort(
        left.card_roles ?? [],
        right.card_roles ?? [],
        component.priorityRoles,
      );
    } else {
      difference = compareNullableManaValue(left.mana_value, right.mana_value);
    }
    if (difference !== 0) return difference;
  }
  return compareStableText(left.name, right.name)
    || compareStableText(left.label, right.label)
    || compareStableText(left.id, right.id);
};

export const compareCardSort = <TCard extends SortableCardLike>(
  left: TCard,
  right: TCard,
  sort: CardSort,
  context: CardSortContext,
): number => {
  if (sort === 'default') {
    return compareDefaultCardSort(left, right, context);
  }
  if (sort === 'name_asc') {
    return left.name.localeCompare(right.name) || left.label.localeCompare(right.label) || left.id.localeCompare(right.id);
  }
  if (sort === 'mana_asc') {
    const leftMana = left.mana_value;
    const rightMana = right.mana_value;
    if (leftMana === null && rightMana !== null) return 1;
    if (leftMana !== null && rightMana === null) return -1;
    if (leftMana !== null && rightMana !== null && leftMana !== rightMana) return leftMana - rightMana;
    return left.name.localeCompare(right.name) || left.label.localeCompare(right.label) || left.id.localeCompare(right.id);
  }
  if (sort === 'mana_desc') {
    const leftMana = left.mana_value;
    const rightMana = right.mana_value;
    if (leftMana === null && rightMana !== null) return 1;
    if (leftMana !== null && rightMana === null) return -1;
    if (leftMana !== null && rightMana !== null && leftMana !== rightMana) return rightMana - leftMana;
    return left.name.localeCompare(right.name) || left.label.localeCompare(right.label) || left.id.localeCompare(right.id);
  }
  if (sort === 'mana_type_asc') {
    return (left.mana_family_sort_key ?? Number.MAX_SAFE_INTEGER)
      - (right.mana_family_sort_key ?? Number.MAX_SAFE_INTEGER)
      || compareStableText(left.name, right.name)
      || compareStableText(left.label, right.label)
      || compareStableText(left.id, right.id);
  }
  if (sort === 'types_asc') {
    return compareCardTypeSort(left, right, context.typeSortLookup)
      || left.name.localeCompare(right.name)
      || left.label.localeCompare(right.label)
      || left.id.localeCompare(right.id);
  }
  return parseTimestamp(right.updated_at) - parseTimestamp(left.updated_at)
    || left.label.localeCompare(right.label)
    || left.id.localeCompare(right.id);
};

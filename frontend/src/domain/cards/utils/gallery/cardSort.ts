export type TypeSortMetadata = {
  key: string;
  label: string;
  linked_card_count?: number;
};

export type CardTypeMetadata = {
  key: string;
  label: string;
};

export type CardSort = 'updated_desc' | 'name_asc' | 'mana_asc' | 'mana_desc' | 'types_asc';

export type CardSortOption = {
  value: CardSort;
  label: string;
  description: string;
};

export const DEFAULT_CARD_SORT: CardSort = 'updated_desc';

export const cardSortOptions: CardSortOption[] = [
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
];

export const isCardSort = (value: unknown): value is CardSort =>
  typeof value === 'string' && cardSortOptions.some((option) => option.value === value);

export const getCardSortLabel = (sort: CardSort): string =>
  cardSortOptions.find((option) => option.value === sort)?.label ?? 'Recently Updated';

export const getCardSortCompactLabel = (sort: CardSort): string => {
  if (sort === 'name_asc') return 'Name';
  if (sort === 'mana_asc') return 'Mana ↑';
  if (sort === 'mana_desc') return 'Mana ↓';
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
  updated_at: string;
  types?: CardTypeMetadata[];
};

type TypeSortLookupEntry = {
  linkedCardCount: number;
  label: string;
};

export type TypeSortLookup = Record<string, TypeSortLookupEntry>;
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

export const compareCardSort = <TCard extends SortableCardLike>(
  left: TCard,
  right: TCard,
  sort: CardSort,
  typeSortLookup?: TypeSortLookup,
): number => {
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
  if (sort === 'types_asc') {
    const leftType = getCardTypeSortValue(left, typeSortLookup);
    const rightType = getCardTypeSortValue(right, typeSortLookup);
    return leftType.bucket - rightType.bucket
      || rightType.linkedCardCount - leftType.linkedCardCount
      || leftType.typeLabel.localeCompare(rightType.typeLabel)
      || left.name.localeCompare(right.name)
      || left.label.localeCompare(right.label)
      || left.id.localeCompare(right.id);
  }
  return parseTimestamp(right.updated_at) - parseTimestamp(left.updated_at)
    || left.label.localeCompare(right.label)
    || left.id.localeCompare(right.id);
};

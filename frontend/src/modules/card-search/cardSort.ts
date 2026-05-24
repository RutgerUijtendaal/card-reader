export type CardSort = 'updated_desc' | 'name_asc' | 'mana_asc' | 'mana_desc';

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
};

const parseTimestamp = (value: string): number => {
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
};

export const compareCardSort = <TCard extends SortableCardLike>(left: TCard, right: TCard, sort: CardSort): number => {
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
  return parseTimestamp(right.updated_at) - parseTimestamp(left.updated_at)
    || left.label.localeCompare(right.label)
    || left.id.localeCompare(right.id);
};

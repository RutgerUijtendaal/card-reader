export const CARD_POOL_OPTIONS = [
  { value: 'player', label: 'Player', rank: 0 },
  { value: 'evil', label: 'Evil', rank: 1 },
  { value: 'neutral', label: 'Neutral', rank: 2 },
] as const;

export type CardPool = (typeof CARD_POOL_OPTIONS)[number]['value'];

const CARD_POOL_SET: ReadonlySet<string> = new Set(CARD_POOL_OPTIONS.map((option) => option.value));

export const isCardPool = (value: unknown): value is CardPool =>
  typeof value === 'string' && CARD_POOL_SET.has(value);

export const normalizeCardPool = (value: unknown): CardPool =>
  isCardPool(value) ? value : 'player';

export const cardPoolLabel = (cardPool: CardPool): string =>
  CARD_POOL_OPTIONS.find((option) => option.value === cardPool)?.label ?? cardPool;

export const DEFAULT_CARD_PAGE_SIZE = 36;
export const CARD_PAGE_SIZE_OPTIONS = [24, 36, 48, 62, 72, 100] as const;

export const normalizeCardPageSize = (value: number): number => {
  const normalized = Math.round(value);
  return CARD_PAGE_SIZE_OPTIONS.includes(normalized as (typeof CARD_PAGE_SIZE_OPTIONS)[number])
    ? normalized
    : DEFAULT_CARD_PAGE_SIZE;
};

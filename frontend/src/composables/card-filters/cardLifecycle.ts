export type CardLifecycleStatus = 'active' | 'deprecated';
export type CardLifecycleFilterValue = CardLifecycleStatus | 'all';
export type CardLifecycleCarrier = {
  lifecycle_status?: CardLifecycleStatus | null;
};
export type CardLifecycleApiParams = {
  lifecycle_status: CardLifecycleFilterValue;
};

export const ACTIVE_CARD_LIFECYCLE_STATUS: CardLifecycleStatus = 'active';
export const DEPRECATED_CARD_LIFECYCLE_STATUS: CardLifecycleStatus = 'deprecated';
export const ALL_CARD_LIFECYCLE_FILTER: CardLifecycleFilterValue = 'all';
export const DEFAULT_CARD_LIFECYCLE_FILTER: CardLifecycleFilterValue = ACTIVE_CARD_LIFECYCLE_STATUS;
export const MANAGEMENT_CARD_LIFECYCLE_FILTER: CardLifecycleFilterValue = ALL_CARD_LIFECYCLE_FILTER;

export const normalizeCardLifecycleFilterValue = (value: unknown): CardLifecycleFilterValue =>
  value === DEPRECATED_CARD_LIFECYCLE_STATUS || value === ALL_CARD_LIFECYCLE_FILTER
    ? value
    : DEFAULT_CARD_LIFECYCLE_FILTER;

export const normalizeCardLifecycleStatus = (value: unknown): CardLifecycleStatus =>
  value === DEPRECATED_CARD_LIFECYCLE_STATUS ? value : ACTIVE_CARD_LIFECYCLE_STATUS;

export const cardIsDeprecated = (card: CardLifecycleCarrier | null | undefined): boolean =>
  normalizeCardLifecycleStatus(card?.lifecycle_status) === DEPRECATED_CARD_LIFECYCLE_STATUS;

export const buildCardLifecycleApiParams = (
  value: unknown,
  { includeDefault = false }: { includeDefault?: boolean } = {},
): CardLifecycleApiParams | undefined => {
  const lifecycleStatus = normalizeCardLifecycleFilterValue(value);
  if (!includeDefault && lifecycleStatus === DEFAULT_CARD_LIFECYCLE_FILTER) {
    return undefined;
  }
  return { lifecycle_status: lifecycleStatus };
};

export const managementCardSearchLifecycleParams = (): CardLifecycleApiParams =>
  buildCardLifecycleApiParams(MANAGEMENT_CARD_LIFECYCLE_FILTER, { includeDefault: true }) ?? {
    lifecycle_status: MANAGEMENT_CARD_LIFECYCLE_FILTER,
  };

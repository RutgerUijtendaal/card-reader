import { isManaTypeKey } from '@/composables/card-gallery/cardSort';

type ManaCurveCardTypeLike = {
  key: string;
};

export type ManaCurveCardLike = {
  mana_value: number | null;
  types?: ManaCurveCardTypeLike[];
};

export type ManaCurveEntryLike<TCard extends ManaCurveCardLike = ManaCurveCardLike> = {
  quantity: number;
  card: TCard;
};

export type ManaCurveBucket = {
  cost: number;
  label: string;
  count: number;
  heightRatio: number;
};

export type ManaCurveSummary = {
  buckets: ManaCurveBucket[];
  totalCards: number;
  maxBucketCount: number;
  uncostedCards: number;
  excludedManaCards: number;
};

export type BuildManaCurveOptions = {
  overflowCost?: number;
};

const DEFAULT_OVERFLOW_COST = 7;

const normalizeManaValue = (value: number | null, overflowCost: number): number | null => {
  if (!Number.isInteger(value) || value === null || value < 0) {
    return null;
  }
  return Math.min(value, overflowCost);
};

const hasManaType = (card: ManaCurveCardLike): boolean =>
  (card.types ?? []).some((type) => isManaTypeKey(type.key));

const buildBucketCosts = (overflowCost: number, hasZeroCostCards: boolean): number[] => {
  const startCost = hasZeroCostCards ? 0 : 1;
  const costs: number[] = [];
  for (let cost = startCost; cost <= overflowCost; cost += 1) {
    costs.push(cost);
  }
  return costs;
};

export const buildManaCurve = <TCard extends ManaCurveCardLike>(
  entries: ManaCurveEntryLike<TCard>[],
  options: BuildManaCurveOptions = {},
): ManaCurveSummary => {
  const overflowCost = options.overflowCost ?? DEFAULT_OVERFLOW_COST;
  const normalizedEntries: Array<{ quantity: number; manaValue: number | null }> = [];
  let totalCards = 0;
  let uncostedCards = 0;
  let excludedManaCards = 0;
  let hasZeroCostCards = false;

  for (const entry of entries) {
    if (hasManaType(entry.card)) {
      excludedManaCards += entry.quantity;
      continue;
    }

    totalCards += entry.quantity;
    const normalizedManaValue = normalizeManaValue(entry.card.mana_value, overflowCost);
    normalizedEntries.push({
      quantity: entry.quantity,
      manaValue: normalizedManaValue,
    });

    if (normalizedManaValue === null) {
      uncostedCards += entry.quantity;
      continue;
    }

    if (normalizedManaValue === 0) {
      hasZeroCostCards = true;
    }
  }

  const bucketCounts = new Map<number, number>();
  for (const cost of buildBucketCosts(overflowCost, hasZeroCostCards)) {
    bucketCounts.set(cost, 0);
  }

  for (const entry of normalizedEntries) {
    const normalizedManaValue = entry.manaValue;
    if (normalizedManaValue === null) {
      continue;
    }
    bucketCounts.set(normalizedManaValue, (bucketCounts.get(normalizedManaValue) ?? 0) + entry.quantity);
  }

  const maxBucketCount = Math.max(...bucketCounts.values(), 0);
  const buckets = [...bucketCounts.entries()].map(([cost, count]) => ({
    cost,
    label: cost === overflowCost ? `${overflowCost}+` : String(cost),
    count,
    heightRatio: maxBucketCount > 0 ? count / maxBucketCount : 0,
  }));

  return {
    buckets,
    totalCards,
    maxBucketCount,
    uncostedCards,
    excludedManaCards,
  };
};

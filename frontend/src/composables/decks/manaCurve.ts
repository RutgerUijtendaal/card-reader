export type ManaCurveCardLike = {
  mana_value: number | null;
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

export const buildManaCurve = <TCard extends ManaCurveCardLike>(
  entries: ManaCurveEntryLike<TCard>[],
  options: BuildManaCurveOptions = {},
): ManaCurveSummary => {
  const overflowCost = options.overflowCost ?? DEFAULT_OVERFLOW_COST;
  const bucketCounts = new Map<number, number>();
  let totalCards = 0;
  let uncostedCards = 0;

  for (let cost = 0; cost <= overflowCost; cost += 1) {
    bucketCounts.set(cost, 0);
  }

  for (const entry of entries) {
    totalCards += entry.quantity;
    const normalizedManaValue = normalizeManaValue(entry.card.mana_value, overflowCost);

    if (normalizedManaValue === null) {
      uncostedCards += entry.quantity;
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
  };
};

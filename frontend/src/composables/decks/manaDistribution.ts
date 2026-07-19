import { isManaTypeKey } from '@/composables/card-gallery/cardSort';

export type ManaDistributionTypeLike = {
  key: string;
};

export type ManaDistributionCardLike = {
  mana_symbols?: string[];
  types?: ManaDistributionTypeLike[];
};

export type ManaDistributionEntryLike<TCard extends ManaDistributionCardLike = ManaDistributionCardLike> = {
  quantity: number;
  card: TCard;
};

export type ManaDistributionSymbolLike = {
  key: string;
  label: string;
  symbol_type: string;
  text_token?: string;
  asset_url?: string | null;
};

export type ManaTypeGroup = {
  id: string;
  name: string;
  typeKeys: string[];
  excludedTypeKeys: string[];
  isVisible: boolean;
};

export type ManaColorStatistics = {
  key: string;
  label: string;
  textToken: string;
  assetUrl: string | null;
  total: number;
  average: number;
  highest: number;
  matchingCards: number;
};

export type ManaTypeGroupStatistics = {
  group: ManaTypeGroup;
  totalCards: number;
  colors: ManaColorStatistics[];
};

export type ManaDistributionSummary = {
  totalCards: number;
  colors: ManaColorStatistics[];
  groups: ManaTypeGroupStatistics[];
};

export type ManaDistributionEntryGroup<TCard extends ManaDistributionCardLike = ManaDistributionCardLike> = {
  group: ManaTypeGroup;
  entries: ManaDistributionEntryLike<TCard>[];
};

const normalizeKey = (value: string): string => value.trim().toLowerCase();

const isColoredManaSymbol = (symbol: ManaDistributionSymbolLike): boolean => {
  const key = normalizeKey(symbol.key);
  return symbol.symbol_type.trim().toLowerCase() === 'mana'
    && key !== 'x'
    && !key.startsWith('colorless-mana-');
};

const isEligibleEntry = (entry: ManaDistributionEntryLike): boolean =>
  !(entry.card.types ?? []).some((type) => isManaTypeKey(type.key));

const normalizedQuantity = (quantity: number): number =>
  Number.isFinite(quantity) ? Math.max(0, Math.floor(quantity)) : 0;

const countManaSymbols = (card: ManaDistributionCardLike): Map<string, number> => {
  const counts = new Map<string, number>();
  for (const rawKey of card.mana_symbols ?? []) {
    const key = normalizeKey(rawKey);
    if (!key) {
      continue;
    }
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return counts;
};

const buildColorStatistics = (
  entries: ManaDistributionEntryLike[],
  colors: ManaDistributionSymbolLike[],
): ManaColorStatistics[] =>
  colors.map((color) => {
    const colorKey = normalizeKey(color.key);
    let total = 0;
    let matchingCards = 0;
    let highest = 0;

    for (const entry of entries) {
      const quantity = normalizedQuantity(entry.quantity);
      const cardPips = countManaSymbols(entry.card).get(colorKey) ?? 0;
      if (quantity === 0 || cardPips === 0) {
        continue;
      }
      total += cardPips * quantity;
      matchingCards += quantity;
      highest = Math.max(highest, cardPips);
    }

    return {
      key: color.key,
      label: color.label,
      textToken: color.text_token?.trim() || `{${color.key}}`,
      assetUrl: color.asset_url ?? null,
      total,
      average: matchingCards > 0 ? total / matchingCards : 0,
      highest,
      matchingCards,
    };
  });

const cardMatchesTypeGroup = (card: ManaDistributionCardLike, group: ManaTypeGroup): boolean => {
  const groupKeys = new Set(group.typeKeys.map(normalizeKey));
  const excludedGroupKeys = new Set(group.excludedTypeKeys.map(normalizeKey));
  const cardTypeKeys = (card.types ?? []).map((type) => normalizeKey(type.key));
  return (groupKeys.size === 0 || cardTypeKeys.some((key) => groupKeys.has(key)))
    && !cardTypeKeys.some((key) => excludedGroupKeys.has(key));
};

export const filterManaDistributionEntriesByTypeGroup = <TCard extends ManaDistributionCardLike>(
  entries: ManaDistributionEntryLike<TCard>[],
  group: ManaTypeGroup,
): ManaDistributionEntryLike<TCard>[] => entries.filter((entry) => cardMatchesTypeGroup(entry.card, group));

export const buildManaDistributionFromEntryGroups = <TCard extends ManaDistributionCardLike>(
  entries: ManaDistributionEntryLike<TCard>[],
  symbols: ManaDistributionSymbolLike[],
  entryGroups: ManaDistributionEntryGroup<TCard>[] = [],
): ManaDistributionSummary => {
  const eligibleEntries: ManaDistributionEntryLike[] = entries.filter(isEligibleEntry);
  const foundSymbolKeys = new Set(
    eligibleEntries.flatMap((entry) => (entry.card.mana_symbols ?? []).map(normalizeKey)),
  );
  const colors = symbols.filter(
    (symbol) => isColoredManaSymbol(symbol) && foundSymbolKeys.has(normalizeKey(symbol.key)),
  );

  return {
    totalCards: eligibleEntries.reduce((total, entry) => total + normalizedQuantity(entry.quantity), 0),
    colors: buildColorStatistics(eligibleEntries, colors),
    groups: entryGroups.map(({ group, entries: groupEntries }) => {
      const eligibleGroupEntries: ManaDistributionEntryLike[] = groupEntries.filter(isEligibleEntry);
      return {
        group,
        totalCards: eligibleGroupEntries.reduce(
          (total, entry) => total + normalizedQuantity(entry.quantity),
          0,
        ),
        colors: buildColorStatistics(eligibleGroupEntries, colors),
      };
    }),
  };
};

export const buildManaDistribution = <TCard extends ManaDistributionCardLike>(
  entries: ManaDistributionEntryLike<TCard>[],
  symbols: ManaDistributionSymbolLike[],
  groups: ManaTypeGroup[] = [],
): ManaDistributionSummary => buildManaDistributionFromEntryGroups(
  entries,
  symbols,
  groups.map((group) => ({
    group,
    entries: filterManaDistributionEntriesByTypeGroup(entries, group),
  })),
);

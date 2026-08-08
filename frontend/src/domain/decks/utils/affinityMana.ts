import type { CardHoverTooltipModel } from '@/domain/cards/types/cardModels';
import type { SymbolFilterOption } from '@/domain/cards/types';

export type HeroAffinityManaPreset = {
  includedManaSymbolKeys: string[];
  excludedManaSymbolKeys: string[];
};

const uniqueSorted = (values: readonly string[]): string[] =>
  [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((left, right) => left.localeCompare(right));

export const getManaSymbolKeysForAffinityKeys = (
  affinitySymbolKeys: readonly string[],
  manaFamilyBySymbolKey: Readonly<Record<string, string>>,
): string[] => uniqueSorted(
  affinitySymbolKeys.map((key) => manaFamilyBySymbolKey[key]).filter((key): key is string => Boolean(key)),
);

const getHeroManaFamilySymbolKeys = (
  hero: Pick<CardHoverTooltipModel, 'symbols'> | null,
  manaFamilyBySymbolKey: Readonly<Record<string, string>>,
): string[] => {
  if (!hero) {
    return [];
  }
  return uniqueSorted(hero.symbols.map((symbol) => symbol.key).filter((key) => manaFamilyBySymbolKey[key]));
};

export const buildHeroAffinityManaPreset = (
  hero: Pick<CardHoverTooltipModel, 'symbols'> | null,
  manaSymbols: readonly SymbolFilterOption[],
  manaFamilyBySymbolKey: Readonly<Record<string, string>>,
): HeroAffinityManaPreset | null => {
  const manaSymbolKeys = uniqueSorted(manaSymbols.map((symbol) => symbol.key));
  const availableManaSymbolKeys = new Set(manaSymbolKeys);
  const includedManaSymbolKeys = getManaSymbolKeysForAffinityKeys(
    getHeroManaFamilySymbolKeys(hero, manaFamilyBySymbolKey),
    manaFamilyBySymbolKey,
  ).filter((key) => availableManaSymbolKeys.has(key));

  if (includedManaSymbolKeys.length === 0) {
    return null;
  }

  const includedManaSymbolKeySet = new Set(includedManaSymbolKeys);
  return {
    includedManaSymbolKeys,
    excludedManaSymbolKeys: manaSymbolKeys.filter((key) => !includedManaSymbolKeySet.has(key)),
  };
};

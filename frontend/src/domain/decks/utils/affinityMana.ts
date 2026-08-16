import type { CardHoverTooltipModel } from '@/domain/cards/types/cardModels';
import type { SymbolFilterOption } from '@/domain/cards/types';

export type HeroManaFamilyPreset = {
  includedManaFamilyKeys: string[];
  excludedManaFamilyKeys: string[];
};

const uniqueSorted = (values: readonly string[]): string[] =>
  [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((left, right) => left.localeCompare(right));

export const getManaFamilyKeysForSymbolKeys = (
  symbolKeys: readonly string[],
  manaFamilyBySymbolKey: Readonly<Record<string, string>>,
): string[] => uniqueSorted(
  symbolKeys.map((key) => manaFamilyBySymbolKey[key]).filter((key): key is string => Boolean(key)),
);

const getHeroManaFamilyKeys = (
  hero: Pick<CardHoverTooltipModel, 'card_mana_families'> | null,
): string[] => {
  if (!hero) {
    return [];
  }
  return uniqueSorted(hero.card_mana_families ?? []);
};

export const buildHeroManaFamilyPreset = (
  hero: Pick<CardHoverTooltipModel, 'card_mana_families'> | null,
  manaSymbols: readonly SymbolFilterOption[],
): HeroManaFamilyPreset | null => {
  const manaFamilyKeys = uniqueSorted(manaSymbols.map((symbol) => symbol.key));
  const availableManaFamilyKeys = new Set(manaFamilyKeys);
  const includedManaFamilyKeys = getHeroManaFamilyKeys(hero).filter((key) =>
    availableManaFamilyKeys.has(key),
  );

  if (includedManaFamilyKeys.length === 0) {
    return null;
  }

  const includedManaFamilyKeySet = new Set(includedManaFamilyKeys);
  return {
    includedManaFamilyKeys,
    excludedManaFamilyKeys: manaFamilyKeys.filter((key) => !includedManaFamilyKeySet.has(key)),
  };
};

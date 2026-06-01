import type { CardHoverTooltipModel } from '@/components/cards/cardModels';
import type { SymbolFilterOption } from '@/modules/card-detail/types';

export const AFFINITY_TO_MANA_SYMBOL_KEYS: Readonly<Record<string, readonly string[]>> = {
  'arcane-affinity': ['arcane-mana'],
  'dark-affinity': ['dark-mana'],
  'divine-affinity': ['divine-mana'],
  'martial-affinity': ['martial-mana'],
  'occult-affinity': ['occult-mana'],
  'primla-affinity': ['primal-mana'],
  'primal-affinity': ['primal-mana'],
};

export type HeroAffinityManaPreset = {
  includedManaSymbolKeys: string[];
  excludedManaSymbolKeys: string[];
};

const uniqueSorted = (values: readonly string[]): string[] =>
  [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((left, right) => left.localeCompare(right));

export const getManaSymbolKeysForAffinityKeys = (affinitySymbolKeys: readonly string[]): string[] =>
  uniqueSorted(affinitySymbolKeys.flatMap((key) => AFFINITY_TO_MANA_SYMBOL_KEYS[key] ?? []));

export const getHeroAffinitySymbolKeys = (hero: Pick<CardHoverTooltipModel, 'symbols'> | null): string[] => {
  if (!hero) {
    return [];
  }
  return uniqueSorted(
    hero.symbols
      .filter((symbol) => symbol.symbol_type === 'affinity')
      .map((symbol) => symbol.key),
  );
};

export const buildHeroAffinityManaPreset = (
  hero: Pick<CardHoverTooltipModel, 'symbols'> | null,
  manaSymbols: readonly SymbolFilterOption[],
): HeroAffinityManaPreset | null => {
  const manaSymbolKeys = uniqueSorted(manaSymbols.map((symbol) => symbol.key));
  const availableManaSymbolKeys = new Set(manaSymbolKeys);
  const includedManaSymbolKeys = getManaSymbolKeysForAffinityKeys(getHeroAffinitySymbolKeys(hero)).filter((key) =>
    availableManaSymbolKeys.has(key),
  );

  if (includedManaSymbolKeys.length === 0) {
    return null;
  }

  const includedManaSymbolKeySet = new Set(includedManaSymbolKeys);
  return {
    includedManaSymbolKeys,
    excludedManaSymbolKeys: manaSymbolKeys.filter((key) => !includedManaSymbolKeySet.has(key)),
  };
};

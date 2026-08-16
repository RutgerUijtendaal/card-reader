import type { CardPool } from '@/domain/cards/cardPools';
import {
  createEmptyCardFilterState,
  normalizeCardFilterState,
  type CardFilterState,
} from '@/domain/cards/utils/filters/cardFilterState';
import type { CardFilterSectionKey } from '@/domain/cards/utils/filters/cardFilterSectionsState';

export const GALLERY_VISIBLE_FILTER_SECTIONS = {
  player: ['mana', 'types', 'affinity', 'devotion', 'generic', 'keywords', 'tags'],
  evil: ['factions', 'types', 'generic', 'keywords', 'tags'],
  neutral: ['types', 'generic', 'keywords', 'tags'],
} as const satisfies Readonly<Record<CardPool, readonly CardFilterSectionKey[]>>;

export const getGalleryVisibleFilterSections = (
  cardPool: CardPool,
): readonly CardFilterSectionKey[] => GALLERY_VISIBLE_FILTER_SECTIONS[cardPool];

export const sanitizeGalleryFilterStateForPool = (
  state: CardFilterState,
  cardPool: CardPool,
): CardFilterState => {
  const normalized = normalizeCardFilterState({ ...state, cardPool });
  const defaults = createEmptyCardFilterState(cardPool);
  const visibleSections = new Set<CardFilterSectionKey>(
    getGalleryVisibleFilterSections(cardPool),
  );

  return normalizeCardFilterState({
    ...normalized,
    cardPool,
    cardRoleMatch: defaults.cardRoleMatch,
    cardRoleKeys: defaults.cardRoleKeys,
    cardRoleExcludeKeys: defaults.cardRoleExcludeKeys,
    cardFactionMatch: visibleSections.has('factions')
      ? normalized.cardFactionMatch
      : defaults.cardFactionMatch,
    cardFactionKeys: visibleSections.has('factions')
      ? normalized.cardFactionKeys
      : defaults.cardFactionKeys,
    cardFactionExcludeKeys: visibleSections.has('factions')
      ? normalized.cardFactionExcludeKeys
      : defaults.cardFactionExcludeKeys,
    manaFamilyMatch: visibleSections.has('mana')
      ? normalized.manaFamilyMatch
      : defaults.manaFamilyMatch,
    manaFamilyKeys: visibleSections.has('mana')
      ? normalized.manaFamilyKeys
      : defaults.manaFamilyKeys,
    manaFamilyExcludeKeys: visibleSections.has('mana')
      ? normalized.manaFamilyExcludeKeys
      : defaults.manaFamilyExcludeKeys,
    manaCostMin: visibleSections.has('mana')
      ? normalized.manaCostMin
      : defaults.manaCostMin,
    manaCostMax: visibleSections.has('mana')
      ? normalized.manaCostMax
      : defaults.manaCostMax,
    affinitySymbolMatch: visibleSections.has('affinity')
      ? normalized.affinitySymbolMatch
      : defaults.affinitySymbolMatch,
    affinitySymbolKeys: visibleSections.has('affinity')
      ? normalized.affinitySymbolKeys
      : defaults.affinitySymbolKeys,
    affinitySymbolExcludeKeys: visibleSections.has('affinity')
      ? normalized.affinitySymbolExcludeKeys
      : defaults.affinitySymbolExcludeKeys,
    devotionSymbolMatch: visibleSections.has('devotion')
      ? normalized.devotionSymbolMatch
      : defaults.devotionSymbolMatch,
    devotionSymbolKeys: visibleSections.has('devotion')
      ? normalized.devotionSymbolKeys
      : defaults.devotionSymbolKeys,
    devotionSymbolExcludeKeys: visibleSections.has('devotion')
      ? normalized.devotionSymbolExcludeKeys
      : defaults.devotionSymbolExcludeKeys,
  });
};

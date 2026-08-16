import type { CardFilterSelectionState } from '@/domain/cards/utils/filters/cardFilterState';
import type { CardFilterSectionKey } from '@/domain/cards/utils/filters/cardFilterSectionsState';

export const DECK_BUILDER_VISIBLE_FILTER_SECTIONS = [
  'mana',
  'types',
  'affinity',
  'devotion',
  'generic',
  'keywords',
  'tags',
] as const satisfies readonly CardFilterSectionKey[];

export const sanitizeDeckBuilderFilterSelection = (
  selection: CardFilterSelectionState,
): CardFilterSelectionState => ({
  ...selection,
  cardRoleMatch: 'any',
  cardRoleIds: [],
  cardRoleExcludeIds: [],
  cardFactionMatch: 'any',
  cardFactionIds: [],
  cardFactionExcludeIds: [],
});

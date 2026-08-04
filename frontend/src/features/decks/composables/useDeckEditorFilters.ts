import type { DeckEditorMode } from '@/features/decks/composables/useDeckEditorDraft';
import { computed, ref, type Ref } from 'vue';
import { MANAGEMENT_CARD_LIFECYCLE_FILTER } from '@/domain/cards/utils/filters/cardLifecycle';
import {
  buildCardFilterApiSearchParams,
  createEmptyCardFilterSelectionState,
  createEmptyCardFilterState,
  type CardFilterSelectionState,
} from '@/domain/cards/utils/filters/cardFilterState';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import { appendCardSortSearchParam } from '@/domain/cards/utils/gallery/cardSort';
import { useCardFilterController } from '@/domain/cards/composables/filters/useCardFilterController';
import { useGalleryOptions } from '@/domain/cards/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/domain/cards/composables/useHoverModePreferences';
import { useCardSortSurface } from '@/domain/cards/composables/useCardSortPreferences';
import { buildHeroAffinityManaPreset } from '@/domain/decks/utils/affinityMana';
import type { DeckCardSummary } from '@/domain/decks/types';

type UseDeckEditorFiltersOptions = {
  deckCardIds: Ref<string[]>;
  editorMode: Ref<DeckEditorMode>;
};

const EMPTY_DECK_SENTINEL_CARD_ID = '__deck-builder-empty__';
const EMPTY_CARD_IDS: string[] = [];
const EMPTY_DECK_SENTINEL_CARD_IDS = [EMPTY_DECK_SENTINEL_CARD_ID];

export const useDeckEditorFilters = ({ deckCardIds, editorMode }: UseDeckEditorFiltersOptions) => {
  const filterController = useCardFilterController();
  const { cardScale } = useGalleryOptions();
  const currentDeckOnly = ref(false);
  const {
    defaultHoverMode,
    overrideHoverMode,
    effectiveHoverMode,
    setOverrideHoverMode,
    clearOverrideHoverMode,
  } = useHoverModeSurface('deckBuilder');
  const {
    defaultSort,
    overrideSort,
    effectiveSort,
    setOverrideSort: setSortOverride,
    clearOverrideSort: clearSortOverride,
  } = useCardSortSurface('deckBuilder');

  const setHoverMode = (value: HoverMode): void => {
    setOverrideHoverMode(value);
  };

  const setCardScale = (value: number): void => {
    cardScale.value = value;
  };

  const setCurrentDeckOnly = (value: boolean): void => {
    currentDeckOnly.value = value;
  };

  let previousCurrentDeckCardIdsSignature = '';
  let previousCurrentDeckCardIds = EMPTY_CARD_IDS;

  const currentDeckCardIds = computed(() => {
    if (!currentDeckOnly.value || editorMode.value !== 'cards') {
      previousCurrentDeckCardIdsSignature = '';
      previousCurrentDeckCardIds = EMPTY_CARD_IDS;
      return EMPTY_CARD_IDS;
    }

    if (deckCardIds.value.length === 0) {
      previousCurrentDeckCardIdsSignature = EMPTY_DECK_SENTINEL_CARD_ID;
      previousCurrentDeckCardIds = EMPTY_DECK_SENTINEL_CARD_IDS;
      return EMPTY_DECK_SENTINEL_CARD_IDS;
    }

    const normalizedCardIds = [...new Set(deckCardIds.value)].sort((left, right) => left.localeCompare(right));
    const signature = normalizedCardIds.join('\u0000');

    if (signature === previousCurrentDeckCardIdsSignature) {
      return previousCurrentDeckCardIds;
    }

    previousCurrentDeckCardIdsSignature = signature;
    previousCurrentDeckCardIds = normalizedCardIds;
    return normalizedCardIds;
  });

  const resetFilters = (): void => {
    filterController.resetFilters();
    currentDeckOnly.value = false;
  };

  const applyHeroAffinityManaPreset = (hero: DeckCardSummary | null): void => {
    resetFilters();
    const preset = buildHeroAffinityManaPreset(hero, filterController.filterCatalog.value.manaSymbols);
    if (!preset) {
      return;
    }

    filterController.applyRouteFilterState({
      ...createEmptyCardFilterState(),
      manaSymbolKeys: preset.includedManaSymbolKeys,
      manaSymbolExcludeKeys: preset.excludedManaSymbolKeys,
    });
  };

  const buildDeckEditorSelectionState = (): CardFilterSelectionState => {
    const selection = filterController.selectionState.value;
    if (editorMode.value === 'cards') {
      return selection;
    }

    return {
      ...createEmptyCardFilterSelectionState(),
      query: selection.query,
      affinitySymbolMatch: selection.affinitySymbolMatch,
      affinitySymbolIds: selection.affinitySymbolIds,
      affinitySymbolExcludeIds: selection.affinitySymbolExcludeIds,
    };
  };

  return {
    filters: filterController.filters,
    filtersLoaded: filterController.filtersLoaded,
    filterSectionsState: filterController.filterSectionsState,
    query: filterController.query,
    selectionState: filterController.selectionState,
    resetFilters,
    applyHeroAffinityManaPreset,
    updateQuery: filterController.updateQuery,
    currentDeckOnly,
    setCurrentDeckOnly,
    currentDeckCardIds,
    defaultHoverMode,
    hoverModeOverride: overrideHoverMode,
    hoverMode: effectiveHoverMode,
    cardScale,
    defaultSort,
    sortOverride: overrideSort,
    effectiveSort,
    setHoverMode,
    clearHoverModeOverride: clearOverrideHoverMode,
    setCardScale,
    setSortOverride,
    clearSortOverride,
    loadFilters: filterController.loadFilters,
    buildSearchParams: () => appendCardSortSearchParam(
      (() => {
        const params = buildCardFilterApiSearchParams(buildDeckEditorSelectionState());
        const cardIds = currentDeckCardIds.value;
        if (cardIds.length > 0) {
          params.set('lifecycle_status', MANAGEMENT_CARD_LIFECYCLE_FILTER);
        }
        cardIds.forEach((cardId) => params.append('card_ids', cardId));
        return params;
      })(),
      effectiveSort.value,
    ),
  };
};

export type DeckEditorFiltersController = ReturnType<typeof useDeckEditorFilters>;

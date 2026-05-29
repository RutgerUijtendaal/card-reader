import type { BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';
import { computed, ref, type Ref } from 'vue';
import { MANAGEMENT_CARD_LIFECYCLE_FILTER } from '@/modules/card-filters/cardLifecycle';
import { buildCardFilterApiSearchParams } from '@/modules/card-filters/cardFilterState';
import type { HoverMode } from '@/modules/card-search/hoverMode';
import { appendCardSortSearchParam } from '@/modules/card-search/cardSort';
import { useCardFilterController } from '@/modules/card-filters/useCardFilterController';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';
import { useHoverModeSurface } from '@/modules/card-search/useHoverModePreferences';
import { useCardSortSurface } from '@/modules/card-search/useCardSortPreferences';

type UseDeckEditorFiltersOptions = {
  deckCardIds: Ref<string[]>;
  builderStep: Ref<BuilderStep>;
};

const EMPTY_DECK_SENTINEL_CARD_ID = '__deck-builder-empty__';
const EMPTY_CARD_IDS: string[] = [];
const EMPTY_DECK_SENTINEL_CARD_IDS = [EMPTY_DECK_SENTINEL_CARD_ID];

export const useDeckEditorFilters = ({ deckCardIds, builderStep }: UseDeckEditorFiltersOptions) => {
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
    if (!currentDeckOnly.value || builderStep.value !== 'build') {
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

  return {
    filters: filterController.filters,
    filtersLoaded: filterController.filtersLoaded,
    filterSectionsState: filterController.filterSectionsState,
    query: filterController.query,
    selectionState: filterController.selectionState,
    resetFilters,
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
        const params = buildCardFilterApiSearchParams(filterController.selectionState.value);
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

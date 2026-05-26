import type { BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';
import { computed, ref, type Ref } from 'vue';
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

  const currentDeckCardIds = computed(() =>
    currentDeckOnly.value && builderStep.value === 'build'
      ? (
          deckCardIds.value.length > 0
            ? [...new Set(deckCardIds.value)].sort((left, right) => left.localeCompare(right))
            : [EMPTY_DECK_SENTINEL_CARD_ID]
        )
      : [],
  );

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
        currentDeckCardIds.value.forEach((cardId) => params.append('card_ids', cardId));
        return params;
      })(),
      effectiveSort.value,
    ),
  };
};

export type DeckEditorFiltersController = ReturnType<typeof useDeckEditorFilters>;

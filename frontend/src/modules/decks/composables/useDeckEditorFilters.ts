import { buildCardFilterApiSearchParams } from '@/modules/card-filters/cardFilterState';
import type { HoverMode } from '@/modules/card-search/hoverMode';
import { appendCardSortSearchParam } from '@/modules/card-search/cardSort';
import { useCardFilterController } from '@/modules/card-filters/useCardFilterController';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';
import { useHoverModeSurface } from '@/modules/card-search/useHoverModePreferences';
import { useCardSortSurface } from '@/modules/card-search/useCardSortPreferences';

export const useDeckEditorFilters = () => {
  const filterController = useCardFilterController();
  const { cardScale } = useGalleryOptions();
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

  return {
    filters: filterController.filters,
    filtersLoaded: filterController.filtersLoaded,
    filterSectionsState: filterController.filterSectionsState,
    query: filterController.query,
    selectionState: filterController.selectionState,
    resetFilters: filterController.resetFilters,
    updateQuery: filterController.updateQuery,
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
      buildCardFilterApiSearchParams(filterController.selectionState.value),
      effectiveSort.value,
    ),
  };
};

export type DeckEditorFiltersController = ReturnType<typeof useDeckEditorFilters>;

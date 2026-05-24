import { buildCardFilterApiSearchParams } from '@/modules/card-filters/cardFilterState';
import { appendCardSortSearchParam } from '@/modules/card-search/cardSort';
import { useCardFilterController } from '@/modules/card-filters/useCardFilterController';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';
import { useCardSortSurface } from '@/modules/card-search/useCardSortPreferences';

export const useDeckEditorFilters = () => {
  const filterController = useCardFilterController();
  const { tooltipEnabled, cardScale } = useGalleryOptions();
  const {
    defaultSort,
    overrideSort,
    effectiveSort,
    setOverrideSort: setSortOverride,
    clearOverrideSort: clearSortOverride,
  } = useCardSortSurface('deckBuilder');

  const setTooltipEnabled = (value: boolean): void => {
    tooltipEnabled.value = value;
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
    tooltipEnabled,
    cardScale,
    defaultSort,
    sortOverride: overrideSort,
    effectiveSort,
    setTooltipEnabled,
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

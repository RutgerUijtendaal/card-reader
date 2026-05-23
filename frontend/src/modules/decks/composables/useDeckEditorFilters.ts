import { buildCardFilterApiSearchParams } from '@/modules/card-filters/cardFilterState';
import { useCardFilterController } from '@/modules/card-filters/useCardFilterController';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';

export const useDeckEditorFilters = () => {
  const filterController = useCardFilterController();
  const { tooltipEnabled, cardScale } = useGalleryOptions();

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
    setTooltipEnabled,
    setCardScale,
    loadFilters: filterController.loadFilters,
    buildSearchParams: () => buildCardFilterApiSearchParams(filterController.selectionState.value),
  };
};

export type DeckEditorFiltersController = ReturnType<typeof useDeckEditorFilters>;

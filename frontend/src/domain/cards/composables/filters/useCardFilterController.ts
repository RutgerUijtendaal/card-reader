import { computed, ref } from 'vue';
import { fetchCardFilters } from '@/domain/cards/api';
import type { CardFiltersResponse } from '@/domain/cards/types';
import { createCardFilterCatalog, type CardFilterState } from '@/domain/cards/utils/filters/cardFilterState';
import { useCardFilterSectionsState } from '@/domain/cards/composables/filters/useCardFilterSectionsState';
import { useCardFilterState } from '@/domain/cards/composables/filters/useCardFilterState';
import { useMetadataFilterFavorites } from '@/domain/cards/composables/filters/useMetadataFilterFavorites';

const EMPTY_FILTERS: CardFiltersResponse = {
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

export const useCardFilterController = () => {
  const filters = ref<CardFiltersResponse>(EMPTY_FILTERS);
  const filtersLoaded = ref(false);
  const filterCatalog = computed(() => createCardFilterCatalog(filters.value));
  const filterState = useCardFilterState(filterCatalog);
  const favorites = useMetadataFilterFavorites();
  const sections = useCardFilterSectionsState(
    filterState,
    filters,
    filterCatalog,
    {
      keywords: favorites.getFavoriteKeys('keywords'),
      tags: favorites.getFavoriteKeys('tags'),
    },
    favorites.toggleFavorite,
  );

  const updateQuery = (value: string): void => {
    filterState.query.value = value;
  };

  const loadFilters = async (): Promise<void> => {
    filters.value = await fetchCardFilters();
    filtersLoaded.value = true;
  };

  const applyRouteFilterState = (state: CardFilterState): void => {
    filterState.applyFilterState(state);
  };

  return {
    filters,
    filtersLoaded,
    filterCatalog,
    filterSectionsState: sections.filterSectionsState,
    query: filterState.query,
    selectionState: filterState.selectionState,
    readFilterState: filterState.readFilterState,
    applyRouteFilterState,
    resetFilters: filterState.reset,
    updateQuery,
    loadFilters,
  };
};

export type CardFilterController = ReturnType<typeof useCardFilterController>;

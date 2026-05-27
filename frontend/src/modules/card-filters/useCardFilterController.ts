import { computed, ref } from 'vue';
import { api } from '@/api/client';
import type { CardFiltersResponse } from '@/modules/card-detail/types';
import { createCardFilterCatalog, type CardFilterState } from '@/modules/card-filters/cardFilterState';
import { useCardFilterSectionsState } from '@/modules/card-filters/useCardFilterSectionsState';
import { useCardFilterState } from '@/modules/card-filters/useCardFilterState';
import { useMetadataFilterFavorites } from '@/modules/card-filters/useMetadataFilterFavorites';

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
    const response = await api.get<CardFiltersResponse>('/cards/filters');
    filters.value = response.data;
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

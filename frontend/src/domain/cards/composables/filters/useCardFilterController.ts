import { computed, ref, toValue, watch, type MaybeRefOrGetter, type WatchSource } from 'vue';
import { fetchCardFilters } from '@/domain/cards/api';
import type { CardPool } from '@/domain/cards/cardPools';
import type { CardFiltersResponse } from '@/domain/cards/types';
import type { CardFilterState } from '@/domain/cards/utils/filters/cardFilterState';
import { createCardFilterCatalog } from '@/domain/cards/utils/filters/cardFilterSelection';
import { useCardFilterSectionsState } from '@/domain/cards/composables/filters/useCardFilterSectionsState';
import { useCardFilterState } from '@/domain/cards/composables/filters/useCardFilterState';
import { useMetadataFilterFavorites } from '@/domain/cards/composables/filters/useMetadataFilterFavorites';

const EMPTY_FILTERS: CardFiltersResponse = {
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

interface CardFilterControllerOptions {
  resultSetKey?: WatchSource<unknown>;
  cardPool?: MaybeRefOrGetter<CardPool>;
}

export const useCardFilterController = (options: CardFilterControllerOptions = {}) => {
  const filters = ref<CardFiltersResponse>(EMPTY_FILTERS);
  const filtersLoaded = ref(false);
  const filtersError = ref<unknown>(null);
  let requestGeneration = 0;
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
    const generation = ++requestGeneration;
    const requestedPool = options.cardPool ? toValue(options.cardPool) : undefined;
    filtersError.value = null;
    let nextFilters: CardFiltersResponse;
    try {
      nextFilters = await fetchCardFilters(requestedPool);
    } catch (error) {
      if (
        generation === requestGeneration
        && (!options.cardPool || requestedPool === toValue(options.cardPool))
      ) {
        filtersError.value = error;
      }
      throw error;
    }
    if (
      generation !== requestGeneration
      || (options.cardPool && requestedPool !== toValue(options.cardPool))
    ) {
      return;
    }
    filters.value = nextFilters;
    filtersLoaded.value = true;
    filtersError.value = null;
  };

  if (options.resultSetKey) {
    watch(
      options.resultSetKey,
      () => {
        requestGeneration += 1;
        filters.value = EMPTY_FILTERS;
        filtersLoaded.value = false;
        filtersError.value = null;
        void loadFilters().catch(() => undefined);
      },
      { flush: 'sync' },
    );
  }

  const applyRouteFilterState = (state: CardFilterState): void => {
    filterState.applyFilterState(state);
  };

  return {
    filters,
    filtersLoaded,
    filtersError,
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

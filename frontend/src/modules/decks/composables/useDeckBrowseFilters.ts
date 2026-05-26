import { computed, ref } from 'vue';
import { api } from '@/api/client';
import type { CardFiltersResponse } from '@/modules/card-detail/types';
import {
  buildDeckBrowseFilterSelectionState,
  buildDeckBrowseFilterStateFromSelection,
  createDeckBrowseFilterCatalog,
  createEmptyDeckBrowseFilterState,
  type DeckBrowseFilterState,
} from '@/modules/decks/deckBrowseFilterState';

const EMPTY_FILTERS: CardFiltersResponse = {
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

export const useDeckBrowseFilters = () => {
  const filters = ref<CardFiltersResponse>(EMPTY_FILTERS);
  const filtersLoaded = ref(false);
  const filterCatalog = computed(() => createDeckBrowseFilterCatalog(filters.value));
  const heroQuery = ref('');
  const cardQuery = ref('');
  const affinitySymbolIds = ref<string[]>([]);
  const affinitySymbolMatch = ref<'any' | 'all'>('any');

  const selectionState = computed(() =>
    buildDeckBrowseFilterSelectionState(readFilterState(), filterCatalog.value),
  );

  function readFilterState(): DeckBrowseFilterState {
    return buildDeckBrowseFilterStateFromSelection(
      {
        heroQuery: heroQuery.value,
        cardQuery: cardQuery.value,
        affinitySymbolMatch: affinitySymbolMatch.value,
        affinitySymbolIds: affinitySymbolIds.value,
      },
      filterCatalog.value,
    );
  }

  const applyRouteFilterState = (state: DeckBrowseFilterState): void => {
    const normalized = buildDeckBrowseFilterSelectionState(state, filterCatalog.value);
    heroQuery.value = normalized.heroQuery;
    cardQuery.value = normalized.cardQuery;
    affinitySymbolMatch.value = normalized.affinitySymbolMatch;
    affinitySymbolIds.value = [...normalized.affinitySymbolIds];
  };

  const resetFilters = (): void => {
    applyRouteFilterState(createEmptyDeckBrowseFilterState());
  };

  const updateHeroQuery = (value: string): void => {
    heroQuery.value = value;
  };

  const updateCardQuery = (value: string): void => {
    cardQuery.value = value;
  };

  const updateAffinitySymbolIds = (value: string[]): void => {
    affinitySymbolIds.value = value;
  };

  const updateAffinitySymbolMatch = (value: 'any' | 'all'): void => {
    affinitySymbolMatch.value = value;
  };

  const resetAffinitySymbols = (): void => {
    affinitySymbolIds.value = [];
    affinitySymbolMatch.value = 'any';
  };

  const loadFilters = async (): Promise<void> => {
    try {
      const response = await api.get<CardFiltersResponse>('/cards/filters');
      filters.value = response.data;
    } finally {
      filtersLoaded.value = true;
    }
  };

  return {
    filtersLoaded,
    filterCatalog,
    heroQuery,
    cardQuery,
    affinitySymbolIds,
    affinitySymbolMatch,
    selectionState,
    readFilterState,
    applyRouteFilterState,
    resetFilters,
    updateHeroQuery,
    updateCardQuery,
    updateAffinitySymbolIds,
    updateAffinitySymbolMatch,
    resetAffinitySymbols,
    loadFilters,
  };
};

export type DeckBrowseFiltersController = ReturnType<typeof useDeckBrowseFilters>;

import { computed, ref } from 'vue';
import { api } from '@/api/client';
import type { CardFiltersResponse } from '@/modules/card-detail/types';
import { fetchDeckTags } from '@/modules/decks/api';
import type { DeckTagCatalog } from '@/modules/decks/types';
import {
  buildDeckBrowseFilterSelectionState,
  buildDeckBrowseFilterStateFromSelection,
  createDeckBrowseFilterCatalog,
  createEmptyDeckBrowseFilterState,
  type DeckBrowseFilterState,
} from '@/composables/decks/deckBrowseFilterState';

const EMPTY_FILTERS: CardFiltersResponse = {
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

export const useDeckBrowseFilters = () => {
  const filters = ref<CardFiltersResponse>(EMPTY_FILTERS);
  const filtersLoaded = ref(false);
  const deckTags = ref<DeckTagCatalog>({ roles: [], types: [] });
  const filterCatalog = computed(() => createDeckBrowseFilterCatalog(filters.value, deckTags.value));
  const query = ref('');
  const affinitySymbolIds = ref<string[]>([]);
  const affinitySymbolExcludeIds = ref<string[]>([]);
  const affinitySymbolMatch = ref<'any' | 'all'>('any');
  const deckTagIds = ref<string[]>([]);
  const deckTagMatch = ref<'any' | 'all'>('any');

  const selectionState = computed(() =>
    buildDeckBrowseFilterSelectionState(readFilterState(), filterCatalog.value),
  );

  function readFilterState(): DeckBrowseFilterState {
    return buildDeckBrowseFilterStateFromSelection(
      {
        query: query.value,
        affinitySymbolMatch: affinitySymbolMatch.value,
        affinitySymbolIds: affinitySymbolIds.value,
        affinitySymbolExcludeIds: affinitySymbolExcludeIds.value,
        deckTagMatch: deckTagMatch.value,
        deckTagIds: deckTagIds.value,
      },
      filterCatalog.value,
    );
  }

  const applyRouteFilterState = (state: DeckBrowseFilterState): void => {
    const normalized = buildDeckBrowseFilterSelectionState(state, filterCatalog.value);
    query.value = normalized.query;
    affinitySymbolMatch.value = normalized.affinitySymbolMatch;
    affinitySymbolIds.value = [...normalized.affinitySymbolIds];
    affinitySymbolExcludeIds.value = [...normalized.affinitySymbolExcludeIds];
    deckTagMatch.value = normalized.deckTagMatch;
    deckTagIds.value = [...normalized.deckTagIds];
  };

  const resetFilters = (): void => {
    applyRouteFilterState(createEmptyDeckBrowseFilterState());
  };

  const updateQuery = (value: string): void => {
    query.value = value;
  };

  const updateAffinitySymbolIds = (value: string[]): void => {
    affinitySymbolIds.value = value;
  };

  const updateAffinitySymbolExcludeIds = (value: string[]): void => {
    affinitySymbolExcludeIds.value = value;
  };

  const updateAffinitySymbolMatch = (value: 'any' | 'all'): void => {
    affinitySymbolMatch.value = value;
  };

  const resetAffinitySymbols = (): void => {
    affinitySymbolIds.value = [];
    affinitySymbolExcludeIds.value = [];
    affinitySymbolMatch.value = 'any';
  };

  const updateDeckTagIds = (value: string[]): void => {
    deckTagIds.value = value;
  };

  const updateDeckTagMatch = (value: 'any' | 'all'): void => {
    deckTagMatch.value = value;
  };

  const resetDeckTags = (): void => {
    deckTagIds.value = [];
    deckTagMatch.value = 'any';
  };

  const loadFilters = async (): Promise<void> => {
    try {
      const [filtersResponse, deckTagResponse] = await Promise.all([
        api.get<CardFiltersResponse>('/cards/filters'),
        fetchDeckTags(),
      ]);
      filters.value = filtersResponse.data;
      deckTags.value = deckTagResponse;
    } finally {
      filtersLoaded.value = true;
    }
  };

  return {
    filtersLoaded,
    filterCatalog,
    query,
    affinitySymbolIds,
    affinitySymbolExcludeIds,
    affinitySymbolMatch,
    deckTagIds,
    deckTagMatch,
    selectionState,
    readFilterState,
    applyRouteFilterState,
    resetFilters,
    updateQuery,
    updateAffinitySymbolIds,
    updateAffinitySymbolExcludeIds,
    updateAffinitySymbolMatch,
    resetAffinitySymbols,
    updateDeckTagIds,
    updateDeckTagMatch,
    resetDeckTags,
    loadFilters,
  };
};

export type DeckBrowseFiltersController = ReturnType<typeof useDeckBrowseFilters>;

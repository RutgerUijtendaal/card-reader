import { computed, ref } from 'vue';
import { fetchCardFilters } from '@/domain/cards/api';
import type { CardFiltersResponse } from '@/domain/cards/types';
import { fetchDeckTags } from '@/domain/decks/api';
import type { DeckTagCatalog } from '@/domain/decks/types';
import {
  buildDeckBrowseFilterSelectionState,
  buildDeckBrowseFilterStateFromSelection,
  createDeckBrowseFilterCatalog,
  createEmptyDeckBrowseFilterState,
  type DeckBrowseFilterState,
} from '@/domain/decks/utils/deckBrowseFilterState';

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
  const filterCatalog = computed(() =>
    createDeckBrowseFilterCatalog(filters.value, deckTags.value),
  );
  const query = ref('');
  const affinitySymbolIds = ref<string[]>([]);
  const affinitySymbolExcludeIds = ref<string[]>([]);
  const affinitySymbolMatch = ref<'any' | 'all'>('any');
  const deckTagIds = ref<string[]>([]);
  const deckTagExcludeIds = ref<string[]>([]);
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
        deckTagExcludeIds: deckTagExcludeIds.value,
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
    deckTagExcludeIds.value = [...normalized.deckTagExcludeIds];
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

  const updateDeckTagExcludeIds = (value: string[]): void => {
    deckTagExcludeIds.value = value;
  };

  const updateDeckTagMatch = (value: 'any' | 'all'): void => {
    deckTagMatch.value = value;
  };

  const resetDeckTags = (): void => {
    deckTagIds.value = [];
    deckTagExcludeIds.value = [];
    deckTagMatch.value = 'any';
  };

  const loadFilters = async (): Promise<void> => {
    try {
      const [filtersResponse, deckTagResponse] = await Promise.all([
        fetchCardFilters(),
        fetchDeckTags(),
      ]);
      filters.value = filtersResponse;
      deckTags.value = deckTagResponse;
    } finally {
      filtersLoaded.value = true;
    }
  };

  return {
    filtersLoaded,
    filterCatalog,
    deckTags,
    query,
    affinitySymbolIds,
    affinitySymbolExcludeIds,
    affinitySymbolMatch,
    deckTagIds,
    deckTagExcludeIds,
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
    updateDeckTagExcludeIds,
    updateDeckTagMatch,
    resetDeckTags,
    loadFilters,
  };
};

export type DeckBrowseFiltersController = ReturnType<typeof useDeckBrowseFilters>;

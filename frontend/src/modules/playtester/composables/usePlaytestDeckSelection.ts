import { computed, ref, watch, type ComputedRef, type Ref } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import { fetchDeckDetail, fetchMyDeck, fetchMyDeckSummaries, fetchPublicDeckSummaries } from '@/modules/decks/api';
import type { DeckRecord, DeckSummaryRecord } from '@/modules/decks/types';
import {
  createInitialPlaytestState,
  getZoneInstances,
  isStoredDraftStale,
  serializePlaytestDraft,
} from '@/modules/playtester/playtestState';
import type {
  PlaytestDeckSuggestion,
  PlaytestStorageAdapter,
  PlaytestZoneId,
  StoredPlaytestDraft,
} from '@/modules/playtester/types';
import type { PlaytestLowerBarStackZone } from '@/modules/playtester/components/PlaytestLowerBar.vue';
import {
  getCollapsedStackZoneIds,
  getPlaytestStackFace,
  PLAYTEST_STACK_DEFINITIONS,
  PLAYTEST_STACK_PLAY_BUDGET_RATIO,
} from '@/modules/playtester/utils/stacks';

export type PreparedPlaytestDeckSelection = {
  path: string;
  deck: DeckRecord;
  draft: StoredPlaytestDraft | null;
};

type UsePlaytestDeckSelectionOptions = {
  authenticated: ComputedRef<boolean>;
  cardScale: Ref<number>;
  storage: PlaytestStorageAdapter;
};

export const suggestionKey = (suggestion: PlaytestDeckSuggestion): string =>
  `${suggestion.source}:${suggestion.deck.id}`;

export const usePlaytestDeckSelection = ({
  authenticated,
  cardScale,
  storage,
}: UsePlaytestDeckSelectionOptions) => {
  const selectorLoading = ref(true);
  const searchQuery = ref('');
  const suggestions = ref<PlaytestDeckSuggestion[]>([]);
  const selectedSuggestionKey = ref<string | null>(null);
  const selectedDeck = ref<DeckRecord | null>(null);
  const selectedPlaytest = ref<ReturnType<typeof createInitialPlaytestState> | null>(null);
  const selectedDraft = ref<StoredPlaytestDraft | null>(null);
  const selectedStaleDraft = ref<StoredPlaytestDraft | null>(null);
  const openStackZone = ref<PlaytestZoneId | null>(null);
  const lowerBarWidth = ref(0);
  const lowerBarHeight = ref(0);
  const deckDetailCache = new Map<string, Promise<DeckRecord>>();
  let suggestionLoadRequestId = 0;
  let selectedDeckLoadRequestId = 0;

  const selectorZoneInstances = (zoneId: PlaytestZoneId) =>
    selectedPlaytest.value ? getZoneInstances(selectedPlaytest.value, zoneId) : [];

  const selectorHandInstances = computed(() => selectorZoneInstances('hand'));
  const filteredSuggestions = computed(() => suggestions.value);
  const ownedSuggestions = computed(() =>
    filteredSuggestions.value.filter((suggestion) => suggestion.source === 'owned').slice(0, 6),
  );
  const publicSuggestions = computed(() => {
    const ownedDeckIds = new Set(
      filteredSuggestions.value
        .filter((suggestion) => suggestion.source === 'owned')
        .map((suggestion) => suggestion.deck.id),
    );
    return filteredSuggestions.value
      .filter((suggestion) => suggestion.source === 'public' && !ownedDeckIds.has(suggestion.deck.id))
      .slice(0, 8);
  });
  const visibleSuggestions = computed(() => [...ownedSuggestions.value, ...publicSuggestions.value]);
  const visibleSuggestionCount = computed(() => visibleSuggestions.value.length);
  const selectedSuggestion = computed(() =>
    visibleSuggestions.value.find((suggestion) => suggestionKey(suggestion) === selectedSuggestionKey.value) ?? null,
  );
  const hasOngoingPlaytest = computed(() => selectedDraft.value !== null);
  const emptyMessage = computed(() =>
    searchQuery.value.trim() ? 'No decks match the current search.' : 'No decks available for playtesting.',
  );

  const collapsedStackZoneIds = computed(() => {
    if (typeof window === 'undefined' || lowerBarWidth.value <= 0) {
      return new Set<PlaytestZoneId>();
    }
    const rootFontSize = Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize) || 16;
    return getCollapsedStackZoneIds(
      lowerBarWidth.value,
      cardScale.value,
      rootFontSize,
      PLAYTEST_STACK_PLAY_BUDGET_RATIO,
    );
  });

  const selectorStackZones = computed<PlaytestLowerBarStackZone[]>(() =>
    PLAYTEST_STACK_DEFINITIONS.map((zone) => ({
      ...zone,
      defaultAction: 'open' as const,
      face: getPlaytestStackFace(selectedPlaytest.value?.stackFaces, zone.id),
      collapsed: collapsedStackZoneIds.value.has(zone.id),
      instances: selectorZoneInstances(zone.id),
    })),
  );

  const openStackLabel = computed(() =>
    PLAYTEST_STACK_DEFINITIONS.find((zone) => zone.id === openStackZone.value)?.label ?? 'Stack',
  );
  const stackOverlayInstances = computed(() => {
    if (!openStackZone.value) {
      return [];
    }
    const instances = selectorZoneInstances(openStackZone.value);
    return openStackZone.value === 'library' ? instances : [...instances].reverse();
  });
  const stackPopoverBottomOffsetPx = computed(() =>
    lowerBarHeight.value > 0 ? lowerBarHeight.value + 12 : 0,
  );

  const nextSuggestionLoadRequestId = (): number => {
    suggestionLoadRequestId += 1;
    return suggestionLoadRequestId;
  };

  const nextSelectedDeckLoadRequestId = (): number => {
    selectedDeckLoadRequestId += 1;
    return selectedDeckLoadRequestId;
  };

  const fetchVisibleDeck = async (targetDeckId: string): Promise<DeckRecord> => {
    if (authenticated.value) {
      try {
        return await fetchMyDeck(targetDeckId);
      } catch {
        return await fetchDeckDetail(targetDeckId);
      }
    }
    return await fetchDeckDetail(targetDeckId);
  };

  const loadVisibleDeck = (targetDeckId: string): Promise<DeckRecord> => {
    const cached = deckDetailCache.get(targetDeckId);
    if (cached) {
      return cached;
    }
    const request = fetchVisibleDeck(targetDeckId).catch((error: unknown) => {
      deckDetailCache.delete(targetDeckId);
      throw error;
    });
    deckDetailCache.set(targetDeckId, request);
    return request;
  };

  const buildSearchParams = (): URLSearchParams | undefined => {
    const query = searchQuery.value.trim();
    if (!query) {
      return undefined;
    }
    const params = new URLSearchParams();
    params.set('q', query);
    return params;
  };

  const clearSelectedDeckPreview = (): void => {
    selectedDeck.value = null;
    selectedPlaytest.value = null;
    selectedDraft.value = null;
    selectedStaleDraft.value = null;
    openStackZone.value = null;
    nextSelectedDeckLoadRequestId();
  };

  const preloadVisibleDeckDetails = (): void => {
    for (const suggestion of visibleSuggestions.value) {
      void loadVisibleDeck(suggestion.deck.id).catch(() => undefined);
    }
  };

  const loadSuggestions = async (requestId = nextSuggestionLoadRequestId()): Promise<void> => {
    selectorLoading.value = true;
    try {
      const params = buildSearchParams();
      const [ownedDecks, publicDecks] = await Promise.all([
        authenticated.value ? fetchMyDeckSummaries(params) : Promise.resolve<DeckSummaryRecord[]>([]),
        fetchPublicDeckSummaries(params),
      ]);
      if (requestId === suggestionLoadRequestId) {
        suggestions.value = [
          ...ownedDecks.map((deck) => ({ deck, source: 'owned' as const })),
          ...publicDecks.map((deck) => ({ deck, source: 'public' as const })),
        ];
        if (!selectedSuggestion.value) {
          selectedSuggestionKey.value = null;
          clearSelectedDeckPreview();
        }
        preloadVisibleDeckDetails();
      }
    } finally {
      if (requestId === suggestionLoadRequestId) {
        selectorLoading.value = false;
      }
    }
  };

  const debouncedLoadSuggestions = useDebounceFn((requestId: number) => {
    void loadSuggestions(requestId);
  }, 250);

  const loadSelectedDeckPreview = async (suggestion: PlaytestDeckSuggestion): Promise<void> => {
    const requestId = nextSelectedDeckLoadRequestId();
    openStackZone.value = null;
    try {
      const loadedDeck = await loadVisibleDeck(suggestion.deck.id);
      if (requestId !== selectedDeckLoadRequestId || selectedSuggestionKey.value !== suggestionKey(suggestion)) {
        return;
      }
      const draft = storage.load(loadedDeck.id);
      const draftIsStale = draft ? isStoredDraftStale(draft, loadedDeck) : false;
      selectedDeck.value = loadedDeck;
      selectedDraft.value = draft && !draftIsStale ? draft : null;
      selectedStaleDraft.value = draft && draftIsStale ? draft : null;
      selectedPlaytest.value = createInitialPlaytestState(loadedDeck);
    } catch {
      if (requestId === selectedDeckLoadRequestId) {
        selectedDeck.value = null;
        selectedPlaytest.value = null;
        selectedDraft.value = null;
        selectedStaleDraft.value = null;
      }
    }
  };

  const selectSuggestion = (suggestion: PlaytestDeckSuggestion): void => {
    selectedSuggestionKey.value = suggestionKey(suggestion);
    clearSelectedDeckPreview();
    void loadSelectedDeckPreview(suggestion);
  };

  const selectedDeckPath = (): string | null =>
    selectedSuggestion.value ? `/playtester/${selectedSuggestion.value.deck.id}` : null;

  const savePreviewAsSelectedDraft = (): StoredPlaytestDraft | null => {
    if (!selectedPlaytest.value) {
      return null;
    }
    const draft = serializePlaytestDraft(selectedPlaytest.value);
    storage.save(draft);
    return draft;
  };

  const prepareContinueSelectedDeck = (): PreparedPlaytestDeckSelection | null => {
    const path = selectedDeckPath();
    if (!path || !selectedDeck.value) {
      return null;
    }
    let draft = selectedDraft.value ?? selectedStaleDraft.value;
    if (!draft) {
      draft = savePreviewAsSelectedDraft();
    }
    return {
      path,
      deck: selectedDeck.value,
      draft,
    };
  };

  const prepareNewSelectedDeck = (): PreparedPlaytestDeckSelection | null => {
    const path = selectedDeckPath();
    if (!path || !selectedSuggestion.value || !selectedDeck.value) {
      return null;
    }
    storage.clear(selectedSuggestion.value.deck.id);
    const draft = savePreviewAsSelectedDraft();
    return {
      path,
      deck: selectedDeck.value,
      draft,
    };
  };

  const openPreviewStack = (zoneId: PlaytestZoneId): void => {
    if (!selectedPlaytest.value || getZoneInstances(selectedPlaytest.value, zoneId).length === 0) {
      return;
    }
    openStackZone.value = openStackZone.value === zoneId ? null : zoneId;
  };

  const closePreviewStack = (): void => {
    openStackZone.value = null;
  };

  const setLowerBarSize = (width: number, height = 0): void => {
    lowerBarWidth.value = width;
    lowerBarHeight.value = height;
  };

  watch(searchQuery, () => {
    selectedSuggestionKey.value = null;
    clearSelectedDeckPreview();
    const requestId = nextSuggestionLoadRequestId();
    selectorLoading.value = true;
    debouncedLoadSuggestions(requestId);
  });

  return {
    closePreviewStack,
    emptyMessage,
    filteredSuggestions,
    hasOngoingPlaytest,
    loadSuggestions,
    openPreviewStack,
    openStackLabel,
    openStackZone,
    ownedSuggestions,
    prepareContinueSelectedDeck,
    prepareNewSelectedDeck,
    publicSuggestions,
    searchQuery,
    selectSuggestion,
    selectedDeck,
    selectedDraft,
    selectedPlaytest,
    selectedStaleDraft,
    selectedSuggestion,
    selectedSuggestionKey,
    selectorHandInstances,
    selectorLoading,
    selectorStackZones,
    setLowerBarSize,
    stackOverlayInstances,
    stackPopoverBottomOffsetPx,
    suggestions,
    visibleSuggestionCount,
  };
};

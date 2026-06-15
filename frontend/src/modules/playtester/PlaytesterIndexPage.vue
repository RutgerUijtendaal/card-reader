<template>
  <section class="playtester-index-page flex flex-col">
    <AppPageHeader
      :icon="Gamepad2"
      title="Playtester"
      subtitle="Choose a deck and run opening hands, setup, and early turns."
      title-tag="h2"
      title-class="text-xl"
    />

    <PlaytestTableSurface
      class="playtester-selector-table"
      :style="cardScaleStyle"
      data-testid="playtester-pre-setup-surface"
      @wheel="handleSelectorWheel"
    >
      <div class="playtester-selector-board" />

      <section
        class="playtester-selector-overlay"
        aria-labelledby="playtester-selector-heading"
      >
        <div class="playtester-selector-panel">
          <header class="playtester-selector-header">
            <div class="min-w-0">
              <p class="playtester-selector-kicker">
                Pre-setup
              </p>
              <h3
                id="playtester-selector-heading"
                class="playtester-selector-title"
              >
                Select Deck
              </h3>
            </div>

            <div class="playtester-selector-count theme-pill theme-pill-neutral text-xs">
              {{ visibleSuggestionCount }} decks
            </div>
          </header>

          <AppSearchInput
            v-model="searchQuery"
            class="playtester-selector-search"
            input-class="h-10 text-sm"
            placeholder="Search by deck, hero, owner, or card"
          />

          <div class="playtester-selector-body app-scrollbar">
            <div
              v-if="loading"
              class="space-y-2"
            >
              <DeckLoadingSkeleton
                v-for="index in 4"
                :key="`playtester-loading-${index}`"
                density="compact"
              />
            </div>

            <div
              v-else-if="filteredSuggestions.length === 0"
              class="playtester-selector-empty"
            >
              {{ emptyMessage }}
            </div>

            <div
              v-else
              class="space-y-5"
            >
              <section
                v-if="ownedSuggestions.length > 0"
                class="space-y-2"
              >
                <div class="playtester-selector-section-heading">
                  <h4>Your Decks</h4>
                  <span>{{ ownedSuggestions.length }}</span>
                </div>

                <div class="space-y-2">
                  <DeckCompactCard
                    v-for="suggestion in ownedSuggestions"
                    :key="`owned-${suggestion.deck.id}`"
                    :deck="suggestion.deck"
                    mode="owned"
                    surface="playtester"
                    :selected="selectedSuggestionKey === suggestionKey(suggestion)"
                    @select="selectSuggestion(suggestion)"
                  />
                </div>
              </section>

              <section
                v-if="publicSuggestions.length > 0"
                class="space-y-2"
              >
                <div class="playtester-selector-section-heading">
                  <h4>Public Decks</h4>
                  <span>{{ publicSuggestions.length }}</span>
                </div>

                <div class="space-y-2">
                  <DeckCompactCard
                    v-for="suggestion in publicSuggestions"
                    :key="`public-${suggestion.deck.id}`"
                    :deck="suggestion.deck"
                    mode="browse"
                    surface="playtester"
                    :selected="selectedSuggestionKey === suggestionKey(suggestion)"
                    @select="selectSuggestion(suggestion)"
                  />
                </div>
              </section>
            </div>
          </div>

          <footer class="playtester-selector-footer">
            <div class="min-w-0">
              <p class="playtester-selector-preview-title">
                {{ selectedSuggestion?.deck.name ?? 'No deck selected' }}
              </p>
              <p class="playtester-selector-preview-meta">
                {{ selectedSuggestion ? `Hero: ${selectedSuggestion.deck.hero_card.name}` : 'Choose a deck from the list.' }}
              </p>
            </div>
            <div class="playtester-selector-actions">
              <button
                v-if="hasOngoingPlaytest"
                class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap"
                type="button"
                :disabled="!selectedSuggestion || !selectedPlaytest"
                @click="startNewSelectedDeck"
              >
                <RotateCcw class="h-4 w-4" />
                <span>New Playtest</span>
              </button>
              <button
                class="btn-primary inline-flex items-center gap-2 whitespace-nowrap"
                type="button"
                :disabled="!selectedSuggestion || (!hasOngoingPlaytest && !selectedPlaytest)"
                @click="continueSelectedDeck"
              >
                <Play class="h-4 w-4" />
                <span>{{ hasOngoingPlaytest ? 'Continue Playtest' : 'Start Playtest' }}</span>
              </button>
            </div>
          </footer>
        </div>
      </section>

      <PlaytestLowerBar
        class="playtester-selector-lower"
        :hand-instances="handInstances"
        :hand-title="selectedPlaytest ? `Opening hand: ${handInstances.length}` : 'Opening hand'"
        :hand-subtitle="selectedPlaytest ? 'Middle-click a card to inspect.' : 'Select a deck to draw a preview hand.'"
        :stack-zones="selectorStackZones"
        :card-back-url="currentCardBackUrl"
        :card-interactive="false"
        :placeholder-hand-size="7"
        :stack-draggable="false"
        @open-stack="openPreviewStack"
        @draw-stack="openPreviewStack"
        @resize="setLowerBarWidth"
      />

      <PlaytestStackPopover
        :open="Boolean(openStackZone)"
        :title="openStackLabel"
        :instances="stackOverlayInstances"
        :card-back-url="currentCardBackUrl"
        :card-interactive="false"
        :bottom-offset-px="stackPopoverBottomOffsetPx"
        test-id="playtester-selector-stack-overlay"
        @close="closePreviewStack"
      />
    </PlaytestTableSurface>
  </section>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core';
import { computed, onMounted, ref, watch } from 'vue';
import { Gamepad2, Play, RotateCcw } from 'lucide-vue-next';
import { useRouter } from 'vue-router';
import { toAbsoluteApiUrl } from '@/api/client';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppSearchInput from '@/components/app/AppSearchInput.vue';
import DeckCompactCard from '@/components/decks/DeckCompactCard.vue';
import DeckLoadingSkeleton from '@/components/decks/DeckLoadingSkeleton.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchDeckDetail, fetchMyDeck, fetchMyDeckSummaries, fetchPublicDeckSummaries } from '@/modules/decks/api';
import type { DeckRecord, DeckSummaryRecord } from '@/modules/decks/types';
import { fetchCurrentCardBack } from '@/modules/playtester/api';
import PlaytestLowerBar, { type PlaytestLowerBarStackZone } from '@/modules/playtester/components/PlaytestLowerBar.vue';
import PlaytestStackPopover from '@/modules/playtester/components/PlaytestStackPopover.vue';
import PlaytestTableSurface from '@/modules/playtester/components/PlaytestTableSurface.vue';
import { createLocalPlaytestStorage } from '@/modules/playtester/localPlaytestStorage';
import {
  createInitialPlaytestState,
  getZoneInstances,
  isStoredDraftStale,
  serializePlaytestDraft,
} from '@/modules/playtester/playtestState';
import type {
  PlaytestDeckSuggestion,
  PlaytestState,
  PlaytestZoneId,
  StoredPlaytestDraft,
} from '@/modules/playtester/types';
import {
  getPlaytestCardScaleStyle,
  loadPlaytestCardScale,
  normalizePlaytestCardScale,
  PLAYTEST_CARD_SCALE_STEP,
  savePlaytestCardScale,
} from '@/modules/playtester/utils/cardScale';
import { setPlaytestRouteHandoff } from '@/modules/playtester/utils/routeHandoff';
import {
  getCollapsedStackZoneIds,
  getPlaytestStackFace,
  PLAYTEST_STACK_DEFINITIONS,
  PLAYTEST_STACK_PLAY_BUDGET_RATIO,
} from '@/modules/playtester/utils/stacks';

const router = useRouter();
const auth = useAuthStore();
const storage = createLocalPlaytestStorage();
const loading = ref(true);
const cardScale = ref(loadPlaytestCardScale());
const searchQuery = ref('');
const suggestions = ref<PlaytestDeckSuggestion[]>([]);
const selectedSuggestionKey = ref<string | null>(null);
const selectedDeck = ref<DeckRecord | null>(null);
const selectedPlaytest = ref<PlaytestState | null>(null);
const selectedDraft = ref<StoredPlaytestDraft | null>(null);
const selectedStaleDraft = ref<StoredPlaytestDraft | null>(null);
const currentCardBackUrl = ref<string | null>(null);
const openStackZone = ref<PlaytestZoneId | null>(null);
const lowerBarWidth = ref(0);
const lowerBarHeight = ref(0);
let suggestionLoadRequestId = 0;
let deckLoadRequestId = 0;
const deckDetailCache = new Map<string, Promise<DeckRecord>>();

const setLowerBarWidth = (width: number, height = 0): void => {
  lowerBarWidth.value = width;
  lowerBarHeight.value = height;
};

const nextSuggestionLoadRequestId = (): number => {
  suggestionLoadRequestId += 1;
  return suggestionLoadRequestId;
};

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
const cardScaleStyle = computed(() => getPlaytestCardScaleStyle(cardScale.value));
const stackPopoverBottomOffsetPx = computed(() =>
  lowerBarHeight.value > 0 ? lowerBarHeight.value + 12 : undefined,
);
const handInstances = computed(() =>
  selectedPlaytest.value ? getZoneInstances(selectedPlaytest.value, 'hand') : [],
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
    collapsed: collapsedStackZoneIds.value.has(zone.id),
    face: getPlaytestStackFace(selectedPlaytest.value?.stackFaces, zone.id),
    instances: selectedPlaytest.value ? getZoneInstances(selectedPlaytest.value, zone.id) : [],
  })),
);
const openStackLabel = computed(() =>
  PLAYTEST_STACK_DEFINITIONS.find((zone) => zone.id === openStackZone.value)?.label ?? 'Stack',
);
const stackOverlayInstances = computed(() => {
  if (!selectedPlaytest.value || !openStackZone.value) {
    return [];
  }
  const instances = getZoneInstances(selectedPlaytest.value, openStackZone.value);
  return openStackZone.value === 'library' ? instances : [...instances].reverse();
});
const emptyMessage = computed(() =>
  searchQuery.value.trim() ? 'No decks match the current search.' : 'No decks available for playtesting.',
);

const suggestionKey = (suggestion: PlaytestDeckSuggestion): string =>
  `${suggestion.source}:${suggestion.deck.id}`;

const buildSearchParams = (): URLSearchParams | undefined => {
  const query = searchQuery.value.trim();
  if (!query) {
    return undefined;
  }
  const params = new URLSearchParams();
  params.set('q', query);
  return params;
};

const loadSuggestions = async (requestId = nextSuggestionLoadRequestId()): Promise<void> => {
  loading.value = true;
  try {
    const params = buildSearchParams();
    const [ownedDecks, publicDecks] = await Promise.all([
      auth.authenticated ? fetchMyDeckSummaries(params) : Promise.resolve<DeckSummaryRecord[]>([]),
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
      loading.value = false;
    }
  }
};

const loadCurrentCardBack = async (): Promise<void> => {
  try {
    const response = await fetchCurrentCardBack();
    currentCardBackUrl.value = response.current?.image_url ? toAbsoluteApiUrl(response.current.image_url) : null;
  } catch {
    currentCardBackUrl.value = null;
  }
};

const debouncedLoadSuggestions = useDebounceFn((requestId: number) => {
  void loadSuggestions(requestId);
}, 250);

const nextDeckLoadRequestId = (): number => {
  deckLoadRequestId += 1;
  return deckLoadRequestId;
};

const clearSelectedDeckPreview = (): void => {
  selectedDeck.value = null;
  selectedPlaytest.value = null;
  selectedDraft.value = null;
  selectedStaleDraft.value = null;
  openStackZone.value = null;
  nextDeckLoadRequestId();
};

const fetchVisibleDeck = async (deckId: string): Promise<DeckRecord> => {
  if (auth.authenticated) {
    try {
      return await fetchMyDeck(deckId);
    } catch {
      return await fetchDeckDetail(deckId);
    }
  }
  return await fetchDeckDetail(deckId);
};

const loadVisibleDeck = (deckId: string): Promise<DeckRecord> => {
  const cached = deckDetailCache.get(deckId);
  if (cached) {
    return cached;
  }
  const request = fetchVisibleDeck(deckId).catch((error: unknown) => {
    deckDetailCache.delete(deckId);
    throw error;
  });
  deckDetailCache.set(deckId, request);
  return request;
};

const preloadVisibleDeckDetails = (): void => {
  for (const suggestion of visibleSuggestions.value) {
    void loadVisibleDeck(suggestion.deck.id).catch(() => undefined);
  }
};

const loadSelectedDeckPreview = async (suggestion: PlaytestDeckSuggestion): Promise<void> => {
  const requestId = nextDeckLoadRequestId();
  openStackZone.value = null;
  try {
    const deck = await loadVisibleDeck(suggestion.deck.id);
    if (requestId !== deckLoadRequestId || selectedSuggestionKey.value !== suggestionKey(suggestion)) {
      return;
    }
    const draft = storage.load(deck.id);
    const draftIsStale = draft ? isStoredDraftStale(draft, deck) : false;
    selectedDeck.value = deck;
    selectedDraft.value = draft && !draftIsStale ? draft : null;
    selectedStaleDraft.value = draft && draftIsStale ? draft : null;
    selectedPlaytest.value = createInitialPlaytestState(deck);
  } catch {
    if (requestId === deckLoadRequestId) {
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

const setSelectedDeckHandoff = (draft: StoredPlaytestDraft | null): void => {
  if (!selectedDeck.value) {
    return;
  }
  setPlaytestRouteHandoff(selectedDeck.value.id, {
    deck: selectedDeck.value,
    draft,
  });
};

const savePreviewAsSelectedDraft = (): StoredPlaytestDraft | null => {
  if (!selectedPlaytest.value) {
    return null;
  }
  const draft = serializePlaytestDraft(selectedPlaytest.value);
  storage.save(draft);
  return draft;
};

const continueSelectedDeck = (): void => {
  const path = selectedDeckPath();
  if (!path) {
    return;
  }
  let draft = selectedDraft.value ?? selectedStaleDraft.value;
  if (!draft) {
    draft = savePreviewAsSelectedDraft();
  }
  setSelectedDeckHandoff(draft);
  void router.push(path);
};

const startNewSelectedDeck = (): void => {
  const path = selectedDeckPath();
  if (!path || !selectedSuggestion.value) {
    return;
  }
  storage.clear(selectedSuggestion.value.deck.id);
  const draft = savePreviewAsSelectedDraft();
  setSelectedDeckHandoff(draft);
  void router.push(path);
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

const setCardScale = (value: number): void => {
  cardScale.value = normalizePlaytestCardScale(value);
  savePlaytestCardScale(cardScale.value);
};

const handleSelectorWheel = (event: WheelEvent): void => {
  if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
    return;
  }
  setCardScale(cardScale.value + (event.deltaY < 0 ? PLAYTEST_CARD_SCALE_STEP : -PLAYTEST_CARD_SCALE_STEP));
  event.preventDefault();
};

watch(searchQuery, () => {
  selectedSuggestionKey.value = null;
  clearSelectedDeckPreview();
  const requestId = nextSuggestionLoadRequestId();
  loading.value = true;
  debouncedLoadSuggestions(requestId);
});

onMounted(() => {
  void loadSuggestions();
  void loadCurrentCardBack();
});
</script>

<style scoped>
.playtester-index-page {
  width: 100%;
  min-height: calc(100dvh - var(--app-page-header-height, 0px));
  height: calc(100dvh - var(--app-page-header-height, 0px));
  overflow: hidden;
}

.playtester-selector-table {
  isolation: isolate;
}

.playtester-selector-board {
  position: relative;
  min-height: 21rem;
  flex: 1 1 auto;
  overflow: hidden;
  border-bottom: 1px solid var(--playtest-border);
}

.playtester-selector-board::after {
  position: absolute;
  inset: 0;
  z-index: 2;
  background: color-mix(in srgb, var(--playtest-surface) 42%, transparent);
  content: "";
  pointer-events: none;
}

.playtester-selector-overlay {
  --playtester-selector-float-top: clamp(1rem, 5vh, 3rem);
  position: absolute;
  inset: 1.25rem 1.25rem calc((var(--playtest-card-width) * 1.42) + 5rem);
  z-index: 20;
  display: grid;
  box-sizing: border-box;
  align-items: start;
  justify-items: center;
  padding-top: var(--playtester-selector-float-top);
  pointer-events: none;
}

.playtester-selector-panel {
  display: grid;
  width: min(47rem, 100%);
  max-height: min(42rem, calc(100% - var(--playtester-selector-float-top)));
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 0.8rem;
  overflow: visible;
  pointer-events: auto;
}

.playtester-selector-header,
.playtester-selector-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-inline: 0.2rem;
}

.playtester-selector-kicker {
  color: var(--playtest-text-soft);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.playtester-selector-title {
  color: var(--playtest-text);
  font-size: 1.3rem;
  font-weight: 900;
}

.playtester-selector-count {
  white-space: nowrap;
}

.playtester-selector-search {
  position: relative;
  color: var(--playtest-text-soft);
}

.playtester-selector-body {
  min-height: 13rem;
  overflow: auto;
  padding: 0 0.15rem;
}

.playtester-selector-empty {
  display: grid;
  min-height: 9rem;
  place-items: center;
  border: 1px dashed color-mix(in srgb, var(--playtest-border) 82%, transparent);
  border-radius: 0.6rem;
  background: color-mix(in srgb, var(--playtest-panel-strong) 24%, transparent);
  color: var(--playtest-text-soft);
  font-size: 0.88rem;
  font-weight: 700;
  text-align: center;
}

.playtester-selector-section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  color: var(--playtest-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.playtester-selector-section-heading h4 {
  color: var(--playtest-text);
  font-size: 0.85rem;
  font-weight: 900;
}

.playtester-selector-footer {
  padding-bottom: 0.2rem;
}

.playtester-selector-preview-title {
  overflow: hidden;
  color: var(--playtest-text);
  font-size: 0.95rem;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playtester-selector-preview-meta {
  overflow: hidden;
  color: var(--playtest-text-soft);
  font-size: 0.78rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playtester-selector-actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}

.playtester-selector-lower {
  z-index: 10;
}

.playtester-selector-lower :deep(.playtest-stack) {
  min-height: calc(var(--playtest-card-width) * 1.55);
}

.playtester-selector-lower :deep(.playtest-stack-empty) {
  border-color: var(--playtest-border);
  background: color-mix(in srgb, var(--playtest-panel-strong) 28%, transparent);
}

@media (max-width: 900px) {
  .playtester-index-page {
    height: auto;
    min-height: calc(100dvh - var(--app-page-header-height, 0px));
    overflow: visible;
  }

  .playtester-selector-table {
    min-height: 42rem;
  }

  .playtester-selector-overlay {
    --playtester-selector-float-top: 0px;
    position: relative;
    inset: auto;
    padding: 1rem;
  }

  .playtester-selector-panel {
    max-height: none;
  }

  .playtester-selector-board {
    min-height: 14rem;
  }

}

@media (max-width: 640px) {
  .playtester-selector-header,
  .playtester-selector-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .playtester-selector-actions,
  .playtester-selector-footer .btn-primary,
  .playtester-selector-footer .btn-secondary {
    justify-content: center;
  }
}
</style>

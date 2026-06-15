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
      data-testid="playtester-pre-setup-surface"
    >
      <div class="playtester-selector-board">
        <div class="playtester-selector-board-label">
          <span>Board</span>
          <span>{{ selectedSuggestion ? selectedSuggestion.deck.name : 'Waiting for deck' }}</span>
        </div>

        <div
          v-if="selectedSuggestion"
          class="playtester-selector-hero-preview"
          aria-hidden="true"
        >
          <img
            v-if="selectedSuggestion.deck.hero_card.image_url"
            :src="toAbsoluteApiUrl(selectedSuggestion.deck.hero_card.image_url)"
            :alt="selectedSuggestion.deck.hero_card.name"
            draggable="false"
          >
          <div
            v-else
            class="playtester-selector-hero-fallback"
          >
            {{ selectedSuggestion.deck.hero_card.name }}
          </div>
        </div>

        <div class="playtester-selector-board-empty">
          {{ selectedSuggestion ? 'Ready to build the opening hand.' : 'Select a deck to start setup.' }}
        </div>
      </div>

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

          <div class="playtester-selector-search">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
            <input
              v-model="searchQuery"
              class="input-base h-10 w-full pl-10 pr-3 text-sm"
              placeholder="Search by deck, hero, owner, or card"
            >
          </div>

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
            <button
              class="btn-primary inline-flex items-center gap-2 whitespace-nowrap"
              type="button"
              :disabled="!selectedSuggestion"
              @click="startSelectedDeck"
            >
              <Play class="h-4 w-4" />
              <span>Start Playtest</span>
            </button>
          </footer>
        </div>
      </section>

      <div class="playtester-selector-lower">
        <section class="playtester-selector-hand">
          <div class="playtester-selector-hand-bar">
            <span>Opening hand</span>
            <span class="theme-section-muted">Cards appear after setup starts.</span>
          </div>
          <div class="playtester-selector-hand-fan">
            <span
              v-for="index in 7"
              :key="`hand-placeholder-${index}`"
              class="playtester-selector-hand-card"
              :class="currentCardBackUrl ? 'playtester-selector-hand-card-image' : ''"
              :style="placeholderHandCardStyle(index - 1)"
            >
              <img
                v-if="currentCardBackUrl"
                :src="currentCardBackUrl"
                alt=""
                draggable="false"
              >
            </span>
          </div>
        </section>

        <div class="playtester-selector-stacks">
          <div
            v-for="stack in placeholderStacks"
            :key="stack"
            class="playtester-selector-stack"
          >
            <span>{{ stack }}</span>
            <span>0</span>
          </div>
        </div>
      </div>
    </PlaytestTableSurface>
  </section>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core';
import { computed, onMounted, ref, watch } from 'vue';
import { Gamepad2, Play, Search } from 'lucide-vue-next';
import { useRouter } from 'vue-router';
import { toAbsoluteApiUrl } from '@/api/client';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import DeckCompactCard from '@/components/decks/DeckCompactCard.vue';
import DeckLoadingSkeleton from '@/components/decks/DeckLoadingSkeleton.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchMyDeckSummaries, fetchPublicDeckSummaries } from '@/modules/decks/api';
import type { DeckSummaryRecord } from '@/modules/decks/types';
import { fetchCurrentCardBack } from '@/modules/playtester/api';
import PlaytestTableSurface from '@/modules/playtester/components/PlaytestTableSurface.vue';
import type { PlaytestDeckSuggestion } from '@/modules/playtester/types';

const router = useRouter();
const auth = useAuthStore();
const loading = ref(true);
const searchQuery = ref('');
const suggestions = ref<PlaytestDeckSuggestion[]>([]);
const selectedSuggestionKey = ref<string | null>(null);
const currentCardBackUrl = ref<string | null>(null);
const placeholderStacks = ['Library', 'Discard', 'Banish', 'Other'];
let suggestionLoadRequestId = 0;

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
      auth.authenticated || !auth.authEnabled ? fetchMyDeckSummaries(params) : Promise.resolve<DeckSummaryRecord[]>([]),
      fetchPublicDeckSummaries(params),
    ]);
    if (requestId === suggestionLoadRequestId) {
      suggestions.value = [
        ...ownedDecks.map((deck) => ({ deck, source: 'owned' as const })),
        ...publicDecks.map((deck) => ({ deck, source: 'public' as const })),
      ];
      if (!selectedSuggestion.value) {
        selectedSuggestionKey.value = null;
      }
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

const selectSuggestion = (suggestion: PlaytestDeckSuggestion): void => {
  selectedSuggestionKey.value = suggestionKey(suggestion);
};

const startSelectedDeck = (): void => {
  if (!selectedSuggestion.value) {
    return;
  }
  void router.push(`/playtester/${selectedSuggestion.value.deck.id}`);
};

const placeholderHandCardStyle = (index: number): Record<string, string | number> => {
  const center = index - 3;
  return {
    marginLeft: index === 0 ? '0' : 'calc(var(--playtest-card-width) * -0.5)',
    transform: `translateY(${Math.abs(center) * 0.28}rem) rotate(${center * 3.6}deg)`,
    zIndex: 20 + index,
  };
};

watch(searchQuery, () => {
  selectedSuggestionKey.value = null;
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
  --playtest-card-width: 7.8rem;
  --playtest-stack-full-width: 7.6rem;
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

.playtester-selector-board-label,
.playtester-selector-hand-bar,
.playtester-selector-stack {
  color: var(--playtest-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.playtester-selector-board-label {
  position: absolute;
  top: 0.85rem;
  left: 1rem;
  z-index: 5;
  display: flex;
  gap: 0.7rem;
}

.playtester-selector-board-empty {
  position: absolute;
  inset: 45% auto auto 50%;
  z-index: 4;
  transform: translate(-50%, -50%);
  color: var(--playtest-text-soft);
  font-size: 0.95rem;
  font-weight: 800;
  pointer-events: none;
}

.playtester-selector-hero-preview {
  position: absolute;
  right: 8%;
  bottom: 12%;
  z-index: 3;
  display: grid;
  width: clamp(7.5rem, 12vw, 10rem);
  aspect-ratio: 63 / 88;
  place-items: stretch;
  overflow: hidden;
  border: 0.22rem solid color-mix(in srgb, var(--playtest-border) 82%, transparent);
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--playtest-panel-strong) 72%, transparent);
  box-shadow: 0 1.3rem 2rem rgba(0, 0, 0, 0.22);
  opacity: 0.72;
  transform: rotate(4deg);
}

.playtester-selector-hero-preview img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.playtester-selector-hero-fallback {
  display: grid;
  place-items: center;
  padding: 0.75rem;
  color: var(--playtest-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  text-align: center;
}

.playtester-selector-overlay {
  position: absolute;
  inset: 1.25rem 1.25rem calc((var(--playtest-card-width) * 1.42) + 5rem);
  z-index: 20;
  display: grid;
  place-items: center;
  pointer-events: none;
}

.playtester-selector-panel {
  display: grid;
  width: min(47rem, 100%);
  max-height: min(42rem, 100%);
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  overflow: hidden;
  border: 1px solid var(--playtest-border);
  border-radius: 0.9rem;
  background: color-mix(in srgb, var(--playtest-panel-strong) 94%, transparent);
  box-shadow: 0 1.6rem 4rem rgba(15, 23, 42, 0.22);
  backdrop-filter: blur(16px);
  pointer-events: auto;
}

.playtester-selector-header,
.playtester-selector-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
}

.playtester-selector-header {
  border-bottom: 1px solid var(--playtest-border);
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
  margin: 1rem 1rem 0;
  color: var(--playtest-text-soft);
}

.playtester-selector-body {
  min-height: 13rem;
  overflow: auto;
  padding: 1rem;
}

.playtester-selector-empty {
  display: grid;
  min-height: 9rem;
  place-items: center;
  border: 1px dashed var(--playtest-border);
  border-radius: 0.7rem;
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
  border-top: 1px solid var(--playtest-border);
  background: color-mix(in srgb, var(--playtest-panel) 72%, transparent);
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

.playtester-selector-lower {
  position: relative;
  z-index: 10;
  display: flex;
  flex: 0 0 auto;
  align-items: stretch;
  gap: 0.75rem;
  overflow: hidden;
  padding: 0.75rem;
  border-top: 1px solid var(--playtest-border);
  background: var(--playtest-panel-muted);
  backdrop-filter: blur(12px);
}

.playtester-selector-hand {
  flex: 1 1 34rem;
  min-width: 0;
  min-height: calc((var(--playtest-card-width) * 1.42) + 4rem);
  overflow: hidden;
  border-right: 1px solid var(--playtest-border);
}

.playtester-selector-hand-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.6rem 0.8rem 0;
}

.playtester-selector-hand-fan {
  display: flex;
  box-sizing: border-box;
  height: calc((var(--playtest-card-width) * 1.42) + 2rem);
  min-width: max-content;
  align-items: flex-end;
  justify-content: center;
  padding: 1.25rem 1.5rem 0.75rem;
}

.playtester-selector-hand-card {
  display: grid;
  width: var(--playtest-card-width);
  aspect-ratio: 63 / 88;
  place-items: stretch;
  overflow: hidden;
  flex: 0 0 auto;
  border: 1px solid var(--playtest-border);
  border-radius: 0.45rem;
  background:
    linear-gradient(145deg, color-mix(in srgb, var(--playtest-panel-strong) 62%, transparent), color-mix(in srgb, var(--playtest-panel-muted) 82%, transparent));
  opacity: 0.55;
}

.playtester-selector-hand-card-image {
  background: color-mix(in srgb, var(--playtest-panel-strong) 42%, transparent);
  opacity: 0.68;
}

.playtester-selector-hand-card img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.playtester-selector-stacks {
  display: flex;
  flex: 0 0 auto;
  align-items: stretch;
  gap: 0.75rem;
}

.playtester-selector-stack {
  display: grid;
  width: var(--playtest-stack-full-width);
  min-height: calc(var(--playtest-card-width) * 1.18);
  place-items: center;
  border: 1px solid var(--playtest-border);
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--playtest-panel-strong) 42%, transparent);
  padding: 0.55rem;
}

.playtester-selector-stack span:first-child {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
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

  .playtester-selector-lower {
    overflow-x: auto;
  }

  .playtester-selector-hand {
    min-width: 23rem;
  }
}

@media (max-width: 640px) {
  .playtester-selector-header,
  .playtester-selector-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .playtester-selector-footer .btn-primary {
    justify-content: center;
  }
}
</style>

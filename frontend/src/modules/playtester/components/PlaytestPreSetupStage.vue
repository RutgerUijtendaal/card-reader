<template>
  <PlaytestTableSurface
    class="playtester-table playtester-selector-table"
    :style="cardScaleStyle"
    data-testid="playtester-pre-setup-surface"
    :data-playtest-hover-actions="0"
    :data-playtest-selected-count="0"
    @wheel="emit('wheel-scale', $event)"
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
          :model-value="searchQuery"
          class="playtester-selector-search"
          input-class="h-10 text-sm"
          placeholder="Search by deck, hero, owner, or card"
          @update:model-value="emit('update:searchQuery', $event)"
        />

        <div class="playtester-selector-body app-scrollbar">
          <div
            v-if="selectorLoading"
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
                  @select="emit('select-suggestion', suggestion)"
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
                  @select="emit('select-suggestion', suggestion)"
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
              @click="emit('start-new-selected')"
            >
              <RotateCcw class="h-4 w-4" />
              <span>New Playtest</span>
            </button>
            <button
              class="btn-primary inline-flex items-center gap-2 whitespace-nowrap"
              type="button"
              :disabled="!selectedSuggestion || (!hasOngoingPlaytest && !selectedPlaytest)"
              @click="emit('continue-selected')"
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
      :hand-instances="selectorHandInstances"
      :hand-title="selectedPlaytest ? `Opening hand: ${selectorHandInstances.length}` : 'Opening hand'"
      :hand-subtitle="selectedPlaytest ? 'Middle-click a card to inspect.' : 'Select a deck to draw a preview hand.'"
      :stack-zones="selectorStackZones"
      :card-back-url="currentCardBackUrl"
      :card-interactive="false"
      :placeholder-hand-size="7"
      :stack-draggable="false"
      @open-stack="emit('open-stack', $event)"
      @draw-stack="emit('open-stack', $event)"
      @resize="(width, height) => emit('resize', width, height)"
    />

    <PlaytestStackPopover
      :open="Boolean(openStackZone)"
      :title="openStackLabel"
      :instances="stackOverlayInstances"
      :dragging-instance-ids="[]"
      :card-back-url="currentCardBackUrl"
      :card-interactive="false"
      :bottom-offset-px="stackPopoverBottomOffsetPx"
      test-id="playtester-selector-stack-overlay"
      @close="emit('close-stack')"
    />
  </PlaytestTableSurface>
</template>

<script setup lang="ts">
import { Play, RotateCcw } from 'lucide-vue-next';
import AppSearchInput from '@/components/app/AppSearchInput.vue';
import DeckCompactCard from '@/components/decks/DeckCompactCard.vue';
import DeckLoadingSkeleton from '@/components/decks/DeckLoadingSkeleton.vue';
import PlaytestLowerBar, { type PlaytestLowerBarStackZone } from '@/modules/playtester/components/PlaytestLowerBar.vue';
import PlaytestStackPopover from '@/modules/playtester/components/PlaytestStackPopover.vue';
import PlaytestTableSurface from '@/modules/playtester/components/PlaytestTableSurface.vue';
import type {
  PlaytestCardInstance,
  PlaytestDeckSuggestion,
  PlaytestState,
  PlaytestZoneId,
} from '@/modules/playtester/types';
import { suggestionKey } from '@/modules/playtester/composables/usePlaytestDeckSelection';

defineProps<{
  cardScaleStyle: Record<string, string>;
  currentCardBackUrl: string | null;
  emptyMessage: string;
  filteredSuggestions: PlaytestDeckSuggestion[];
  hasOngoingPlaytest: boolean;
  openStackLabel: string;
  openStackZone: PlaytestZoneId | null;
  ownedSuggestions: PlaytestDeckSuggestion[];
  publicSuggestions: PlaytestDeckSuggestion[];
  searchQuery: string;
  selectedPlaytest: PlaytestState | null;
  selectedSuggestion: PlaytestDeckSuggestion | null;
  selectedSuggestionKey: string | null;
  selectorHandInstances: PlaytestCardInstance[];
  selectorLoading: boolean;
  selectorStackZones: PlaytestLowerBarStackZone[];
  stackOverlayInstances: PlaytestCardInstance[];
  stackPopoverBottomOffsetPx: number;
  visibleSuggestionCount: number;
}>();

const emit = defineEmits<{
  (e: 'close-stack'): void;
  (e: 'continue-selected'): void;
  (e: 'open-stack', zoneId: PlaytestZoneId): void;
  (e: 'resize', width: number, height: number): void;
  (e: 'select-suggestion', suggestion: PlaytestDeckSuggestion): void;
  (e: 'start-new-selected'): void;
  (e: 'update:searchQuery', query: string): void;
  (e: 'wheel-scale', event: WheelEvent): void;
}>();
</script>

<style scoped>
.playtester-selector-table {
  isolation: isolate;
}

.playtester-selector-board {
  position: relative;
  min-height: 21rem;
  flex: 1 1 auto;
  overflow: hidden;
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

<template>
  <section
    v-if="deck"
    class="flex h-[calc(100vh-3rem)] min-h-0 flex-col gap-5 overflow-hidden"
  >
    <div class="page-card flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="min-w-0">
        <h2 class="theme-section-title text-xl font-semibold">
          {{ deck.name }}
        </h2>
        <p class="theme-section-muted text-sm">
          By {{ deck.owner.username }}
        </p>
        <p
          v-if="deck.description"
          class="theme-section-title mt-3 text-sm"
        >
          {{ deck.description }}
        </p>
        <div class="mt-3 flex flex-wrap gap-2 text-xs">
          <span class="theme-pill theme-pill-accent">
            {{ deck.totals.overall_total_cards }} total cards
          </span>
          <span class="theme-pill theme-pill-neutral">
            {{ deck.totals.mainboard_total_cards }} mainboard cards
          </span>
        </div>
      </div>

      <div class="flex flex-wrap gap-2 lg:shrink-0">
        <RouterLink
          class="btn-secondary"
          :to="backLink"
        >
          {{ backLabel }}
        </RouterLink>
        <RouterLink
          v-if="canEdit"
          class="btn-primary"
          :to="buildDeckDetailEditorLocation(deck.id)"
        >
          Edit Deck
        </RouterLink>
      </div>
    </div>

    <div class="grid min-h-0 flex-1 gap-5 overflow-hidden xl:grid-cols-[360px_minmax(0,1fr)]">
      <div class="page-card flex min-h-0 flex-col">
        <div class="app-scrollbar flex-1 overflow-y-auto pr-1">
          <div class="flex min-h-full flex-col">
            <div class="space-y-4">
              <h3 class="theme-section-title text-base font-semibold">
                Hero
              </h3>
              <div class="space-y-3">
                <div class="theme-card-frame theme-card-image-well mx-auto aspect-[63/88] w-full max-w-[22rem] overflow-hidden rounded-2xl">
                  <img
                    v-if="deck.hero_card.image_url"
                    :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
                    :alt="deck.hero_card.name"
                    class="h-full w-full object-cover"
                  >
                  <div
                    v-else
                    class="theme-kicker flex h-full items-center justify-center text-xs"
                  >
                    No image
                  </div>
                </div>

                <p class="theme-section-title text-lg font-semibold">
                  {{ deck.hero_card.name }}
                </p>
              </div>
            </div>

            <div class="mt-auto pt-6">
              <DeckManaCurve
                :entries="activeBoardEntries"
                :empty-label="activeBoardEmptyLabel"
              />
            </div>
          </div>
        </div>

        <div class="theme-divider mt-4 flex shrink-0 flex-wrap items-center gap-3 border-t pt-4">
          <CardSortMenu
            :sort="effectiveSort"
            :default-sort="defaultSort"
            :override-active="deckDetailSortOverride !== null"
            allow-default-option
            @update:sort="setDeckDetailSortOverride"
            @reset="clearDeckDetailSortOverride"
          />
          <GalleryOptionsMenu
            :hover-mode="effectiveHoverMode"
            :default-hover-mode="defaultHoverMode"
            :hover-mode-override-active="deckDetailHoverModeOverride !== null"
            allow-hover-mode-default-option
            :card-scale="cardScale"
            :show-card-groups="false"
            :show-card-groups-control="false"
            @update:hover-mode="setDeckDetailHoverModeOverride"
            @reset:hover-mode="clearDeckDetailHoverModeOverride"
            @update:card-scale="cardScale = $event"
          />
          <button
            class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap"
            type="button"
            @click="handleTtsExport"
          >
            <Download class="h-4 w-4" />
            <span>Export TTS</span>
          </button>
        </div>
      </div>

      <div class="page-card flex min-h-0 flex-col space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <button
              class="theme-pill text-xs"
              :class="activeBoardId === 'mainboard' ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="activeBoardId = 'mainboard'"
            >
              Mainboard
              <span class="ml-1 opacity-80">
                {{ deck.mainboard.total_cards }} / {{ deck.mainboard.unique_cards }}
              </span>
            </button>
            <button
              v-for="sideboard in deck.sideboards"
              :key="sideboard.id"
              class="theme-pill text-xs"
              :class="activeBoardId === sideboard.id ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="activeBoardId = sideboard.id"
            >
              {{ sideboard.name }}
              <span class="ml-1 opacity-80">
                {{ sideboard.total_cards }} / {{ sideboard.unique_cards }}
              </span>
            </button>
          </div>

          <span class="theme-pill theme-pill-neutral shrink-0 text-xs">
            {{ deck.totals.overall_total_cards }} total across all boards
          </span>
        </div>

        <div class="sr-only">
          <h3>
            {{ activeBoardTitle }}
          </h3>
        </div>

        <div class="app-scrollbar min-h-0 flex-1 overflow-y-auto pr-1">
          <div
            class="grid gap-4 px-1 pb-3 pt-2"
            :style="mainboardGridStyle"
          >
            <CardGalleryItem
              v-for="entry in sortedActiveBoardEntries"
              :key="entry.card.id"
              class="justify-self-center"
              :style="mainboardCardStyle"
              :card="toGalleryCard(entry.card)"
              :card-height-rem="mainboardCardHeightRem"
              :hover-mode="effectiveHoverMode"
              :navigation-target="detailLocation(entry.card.id)"
            >
              <template #overlay>
                <div class="absolute inset-x-3 bottom-3 flex items-center justify-start gap-3">
                  <DeckCardCountBadge :quantity="entry.quantity" />
                </div>
              </template>
            </CardGalleryItem>
          </div>
        </div>
      </div>
    </div>
  </section>

  <div
    v-else
    class="page-card theme-section-muted text-sm"
  >
    Loading deck...
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Download } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import { api, toAbsoluteApiUrl } from '@/api/client';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import CardSortMenu from '@/components/cards/CardSortMenu.vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import type { CardFiltersResponse, CardListItem } from '@/modules/card-detail/types';
import { buildTypeSortLookup, compareCardSort } from '@/modules/card-search/cardSort';
import { useCardSortSurface } from '@/modules/card-search/useCardSortPreferences';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';
import { useHoverModeSurface } from '@/modules/card-search/useHoverModePreferences';
import { fetchDeckDetail, fetchMyDeck } from '@/modules/decks/api';
import DeckCardCountBadge from '@/modules/decks/components/DeckCardCountBadge.vue';
import DeckManaCurve from '@/modules/decks/components/DeckManaCurve.vue';
import { buildDeckCardDetailLocation, buildDeckDetailEditorLocation } from '@/modules/decks/deckRouteState';
import type { DeckCardSummary, DeckEntrySummary, DeckRecord, DeckSideboardRecord } from '@/modules/decks/types';
import { useDeckExport } from '@/modules/decks/useDeckExport';

const route = useRoute();
const auth = useAuthStore();
const deck = ref<DeckRecord | null>(null);
const filterOptions = ref<CardFiltersResponse>({
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
});
const { cardScale } = useGalleryOptions();
const {
  defaultSort,
  overrideSort: deckDetailSortOverride,
  effectiveSort,
  setOverrideSort,
  clearOverrideSort,
} = useCardSortSurface('deckDetail');
const {
  defaultHoverMode,
  overrideHoverMode: deckDetailHoverModeOverride,
  effectiveHoverMode,
  setOverrideHoverMode,
  clearOverrideHoverMode,
} = useHoverModeSurface('deckDetail');
const { exportTtsDeck } = useDeckExport();
const activeBoardId = ref('mainboard');
const isOwnedRoute = computed(() => route.path.startsWith('/my/decks/'));

const canEdit = computed(() => deck.value?.owner.id === auth.user?.id);
const backLink = computed(() => (isOwnedRoute.value ? '/my/decks' : '/decks'));
const backLabel = computed(() => (isOwnedRoute.value ? 'Back to My Decks' : 'Back to Decks'));
const mainboardCardHeightRem = computed(() => Number((24 * cardScale.value).toFixed(2)));
const mainboardCardWidthRem = computed(() => Number(((mainboardCardHeightRem.value * 63) / 88).toFixed(2)));
const mainboardGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round((mainboardCardWidthRem.value + 1) * 16)}px, 1fr))`,
}));
const mainboardCardStyle = computed(() => ({
  width: '100%',
  maxWidth: `${mainboardCardWidthRem.value}rem`,
}));
const activeSideboard = computed<DeckSideboardRecord | null>(
  () => deck.value?.sideboards.find((sideboard) => sideboard.id === activeBoardId.value) ?? null,
);
const activeBoardEntries = computed<DeckEntrySummary[]>(() => {
  if (!deck.value) {
    return [];
  }
  return activeBoardId.value === 'mainboard' ? deck.value.mainboard.entries : (activeSideboard.value?.entries ?? []);
});
const activeBoardTitle = computed(() =>
  activeBoardId.value === 'mainboard' ? 'Mainboard' : (activeSideboard.value?.name ?? 'Sideboard'),
);
const activeBoardEmptyLabel = computed(() =>
  activeBoardId.value === 'mainboard' ? 'This deck does not have any mainboard cards yet.' : 'This sideboard does not have any cards yet.',
);
const typeSortLookup = computed(() => buildTypeSortLookup(filterOptions.value.types));
const sortedActiveBoardEntries = computed(() =>
  [...activeBoardEntries.value].sort((left, right) =>
    compareCardSort(left.card, right.card, effectiveSort.value, typeSortLookup.value),
  ),
);
const detailLocation = (cardId: string) => buildDeckCardDetailLocation(cardId, String(route.params.id), route.query);

const setDeckDetailSortOverride = (value: typeof effectiveSort.value): void => {
  setOverrideSort(value);
};

const clearDeckDetailSortOverride = (): void => {
  clearOverrideSort();
};

const setDeckDetailHoverModeOverride = (value: typeof effectiveHoverMode.value): void => {
  setOverrideHoverMode(value);
};

const clearDeckDetailHoverModeOverride = (): void => {
  clearOverrideHoverMode();
};

const toGalleryCard = (card: DeckCardSummary): CardListItem => ({
  ...card,
  result_type: 'card',
});

const loadDeck = async (): Promise<void> => {
  deck.value = isOwnedRoute.value ? await fetchMyDeck(String(route.params.id)) : await fetchDeckDetail(String(route.params.id));
  activeBoardId.value = 'mainboard';
};

const loadFilterOptions = async (): Promise<void> => {
  const response = await api.get<CardFiltersResponse>('/cards/filters');
  filterOptions.value = response.data;
};

const handleTtsExport = async (): Promise<void> => {
  if (!deck.value) {
    return;
  }
  await exportTtsDeck(deck.value.id, deck.value.name);
};

onMounted(async () => {
  await Promise.all([loadDeck(), loadFilterOptions()]);
});
</script>

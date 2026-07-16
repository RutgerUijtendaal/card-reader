<template>
  <DeckDetailLoadingSkeleton
    v-if="loadingInitial"
    :back-to="backLink"
    :back-label="backLabel"
    :grid-style="mainboardGridStyle"
    :card-style="mainboardCardStyle"
    :group-by-type="groupByType"
  />

  <section
    v-else-if="deck"
    class="flex flex-col gap-5"
  >
    <AppPageHeader
      :icon="BookOpenText"
      :title="deck.name"
      :subtitle="deck.description || 'Inspect hero, boards, and included cards.'"
      :back-to="backLink"
      :back-label="backLabel"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #titleMeta>
        <div class="theme-section-muted flex items-center gap-2 text-sm">
          <span>By</span>
          <span class="theme-pill theme-pill-keyword text-xs">
            {{ deck.owner.username }}
          </span>
        </div>
      </template>

      <template #actions>
        <button
          v-if="canEdit && canShare"
          class="btn-secondary"
          type="button"
          @click="copyShareLink"
        >
          Copy Share Link
        </button>
        <button
          class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap"
          type="button"
          @click="handleTtsExport"
        >
          <Clipboard class="h-4 w-4" />
          <span>{{ ttsExportButtonLabel }}</span>
        </button>
        <RouterLink
          class="btn-primary"
          :to="`/playtester/${deck.id}`"
        >
          Playtest
        </RouterLink>
        <RouterLink
          v-if="canEdit"
          class="btn-secondary"
          :to="buildDeckDetailEditorLocation(deck.id)"
        >
          Edit Deck
        </RouterLink>
      </template>
    </AppPageHeader>

    <AppPageLayout
      columns="one"
      :root-class="detailsExpanded ? 'deck-detail-layout deck-detail-layout-expanded' : 'deck-detail-layout'"
    >
      <template #aside>
        <div
          class="deck-detail-aside-shell"
          :class="detailsExpanded ? 'deck-detail-aside-shell-expanded' : ''"
        >
          <AppStickyAside
            root-class="deck-detail-primary-aside"
            scroll-class="space-y-5"
          >
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

            <div class="space-y-3">
              <DeckManaCurve
                :entries="activeBoardEntries"
                :empty-label="activeBoardEmptyLabel"
              />
              <button
                class="deck-mana-details-button theme-section-muted flex w-full items-center justify-between gap-3 border-t pt-3 text-sm font-medium"
                type="button"
                :aria-expanded="detailsExpanded"
                aria-controls="deck-mana-distribution-panel"
                @click="detailsExpanded = !detailsExpanded"
              >
                <span>Details</span>
                <ChevronRight
                  class="h-4 w-4 transition-transform duration-200"
                  :class="detailsExpanded ? 'rotate-90' : ''"
                />
              </button>
            </div>

            <div class="theme-divider border-t pt-4">
              <label class="theme-muted-panel flex items-center gap-3 p-3 text-sm">
                <input
                  v-model="groupByType"
                  type="checkbox"
                  class="theme-checkbox h-4 w-4"
                >
                <span class="theme-section-title font-medium">Group by type</span>
              </label>
            </div>

            <template #footer>
              <div class="flex flex-wrap items-center gap-3">
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
              </div>
            </template>
          </AppStickyAside>

          <Transition name="deck-mana-details">
            <AppStickyAside
              v-if="detailsExpanded"
              id="deck-mana-distribution-panel"
              root-class="deck-detail-distribution-aside"
              scroll-class="space-y-5"
            >
              <DeckManaDistribution
                :entries="activeBoardEntries"
                :symbols="filterOptions.symbols"
                :types="filterOptions.types"
              />
            </AppStickyAside>
          </Transition>
        </div>
      </template>

      <section class="space-y-4">
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

        <div
          v-if="!groupByType"
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
        <div
          v-else
          class="space-y-6 px-1 pb-3 pt-2"
        >
          <section
            v-for="group in groupedActiveBoardEntries"
            :key="group.key"
            class="space-y-3"
            data-testid="deck-type-group"
            :data-type-group-key="group.key"
          >
            <div class="flex items-center justify-between gap-3">
              <h3 class="theme-section-title text-sm font-semibold">
                {{ group.label }}
              </h3>
              <span class="theme-pill theme-pill-neutral text-xs">
                {{ group.entries.reduce((sum, entry) => sum + entry.quantity, 0) }} cards
              </span>
            </div>
            <div
              class="grid gap-4"
              :style="mainboardGridStyle"
            >
              <CardGalleryItem
                v-for="entry in group.entries"
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
          </section>
        </div>
      </section>
    </AppPageLayout>
  </section>

  <div
    v-else
    class="page-card theme-section-muted text-sm"
  >
    Deck not found.
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useLocalStorage } from '@vueuse/core';
import { BookOpenText, ChevronRight, Clipboard } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import { toast } from 'vue-sonner';
import { api, toAbsoluteApiUrl } from '@/api/client';
import AppPageLayout from '@/components/app/AppPageLayout.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppStickyAside from '@/components/app/AppStickyAside.vue';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import CardSortMenu from '@/components/cards/CardSortMenu.vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { buildCardReturnLocation, isCardReturnQuery } from '@/composables/cards/cardReturnState';
import type { CardFiltersResponse, CardListItem } from '@/modules/card-detail/types';
import { buildTypeSortLookup, compareCardSort } from '@/composables/card-gallery/cardSort';
import { useCardSortSurface } from '@/composables/useCardSortPreferences';
import { useGalleryOptions } from '@/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/composables/useHoverModePreferences';
import { fetchDeckDetail, fetchMyDeck } from '@/modules/decks/api';
import DeckCardCountBadge from '@/modules/decks/components/DeckCardCountBadge.vue';
import DeckDetailLoadingSkeleton from '@/modules/decks/components/DeckDetailLoadingSkeleton.vue';
import DeckManaDistribution from '@/modules/decks/components/DeckManaDistribution.vue';
import DeckManaCurve from '@/modules/decks/components/DeckManaCurve.vue';
import { buildDeckCardDetailLocation, buildDeckDetailEditorLocation } from '@/composables/decks/deckRouteState';
import { groupDeckEntriesByType } from '@/composables/decks/deckTypeGroups';
import { buildDeckShareUrl, canShareDeck } from '@/composables/decks/share';
import type { DeckCardSummary, DeckEntrySummary, DeckRecord, DeckSideboardRecord } from '@/modules/decks/types';
import { useDeckExport } from '@/composables/useDeckExport';

const route = useRoute();
const auth = useAuthStore();
const deck = ref<DeckRecord | null>(null);
const loadingInitial = ref(true);
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
const detailsExpanded = ref(false);
const groupByType = useLocalStorage('card-reader.deck-detail-group-by-type', true, {
  writeDefaults: true,
});
const isOwnedRoute = computed(() => route.path.startsWith('/my/decks/'));

const canEdit = computed(() => deck.value?.owner.id === auth.user?.id);
const canShare = computed(() => (deck.value ? canShareDeck(deck.value) : false));
const backLink = computed(() => {
  if (isCardReturnQuery(route.query)) {
    return buildCardReturnLocation(route.query);
  }
  return isOwnedRoute.value ? '/my/decks' : '/decks';
});
const backLabel = computed(() => {
  if (isCardReturnQuery(route.query)) {
    return 'Back to Card';
  }
  return isOwnedRoute.value ? 'Back to My Decks' : 'Back to Decks';
});
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
const ttsExportButtonLabel = computed(() =>
  activeBoardId.value === 'mainboard' ? 'Copy Mainboard TTS' : 'Copy Sideboard TTS',
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
const groupedActiveBoardEntries = computed(() =>
  groupDeckEntriesByType(activeBoardEntries.value, filterOptions.value.types, {
    compareEntries: effectiveSort.value === 'types_asc'
      ? undefined
      : (left, right) => compareCardSort(left.card, right.card, effectiveSort.value, typeSortLookup.value),
  }),
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
  if (activeSideboard.value) {
    await exportTtsDeck(deck.value.id, {
      sideboardId: activeSideboard.value.id,
      successMessage: 'TTS sideboard copied to clipboard',
    });
    return;
  }
  await exportTtsDeck(deck.value.id, {
    successMessage: 'TTS mainboard copied to clipboard',
  });
};

const copyShareLink = async (): Promise<void> => {
  if (!deck.value || !canShare.value) {
    return;
  }
  await navigator.clipboard.writeText(buildDeckShareUrl(deck.value.id));
  toast.success('Share link copied.');
};

onMounted(async () => {
  try {
    await Promise.all([loadDeck(), loadFilterOptions()]);
  } finally {
    loadingInitial.value = false;
  }
});
</script>

<style scoped>
.deck-detail-aside-shell {
  min-width: 0;
}

.deck-mana-details-button {
  border-color: color-mix(in srgb, var(--color-border) 62%, transparent 38%);
  transition: color 180ms ease;
}

.deck-mana-details-button:hover {
  color: var(--color-text);
}

.deck-mana-details-enter-active,
.deck-mana-details-leave-active {
  overflow: hidden;
  transition:
    max-height 240ms ease,
    opacity 180ms ease,
    transform 240ms ease;
}

.deck-mana-details-enter-from,
.deck-mana-details-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-0.5rem);
}

.deck-mana-details-enter-to,
.deck-mana-details-leave-from {
  max-height: 100rem;
  opacity: 1;
  transform: translateY(0);
}

@media (min-width: 1280px) {
  :deep(.deck-detail-layout) {
    grid-template-columns: 22.5rem minmax(0, 1fr);
    transition: grid-template-columns 240ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  :deep(.deck-detail-layout-expanded) {
    grid-template-columns: 45rem minmax(0, 1fr);
  }

  .deck-detail-aside-shell {
    display: grid;
    grid-template-columns: 22.5rem 0;
    overflow: clip;
    transition: grid-template-columns 240ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .deck-detail-aside-shell-expanded {
    grid-template-columns: 22.5rem 22.5rem;
  }

  :deep(.deck-detail-primary-aside) {
    z-index: 1;
  }

  :deep(.deck-detail-distribution-aside) {
    min-width: 0;
    overflow: hidden;
    border-right-width: 1px;
    border-left-width: 1px;
  }

  .deck-mana-details-enter-active,
  .deck-mana-details-leave-active {
    max-height: none;
    transition:
      opacity 180ms ease,
      transform 240ms ease;
  }

  .deck-mana-details-enter-from,
  .deck-mana-details-leave-to {
    max-height: none;
    transform: translateX(-0.75rem);
  }
}

@media (prefers-reduced-motion: reduce) {
  :deep(.deck-detail-layout),
  .deck-detail-aside-shell,
  .deck-mana-details-enter-active,
  .deck-mana-details-leave-active,
  .deck-mana-details-button,
  .deck-mana-details-button :deep(svg) {
    transition-duration: 0.01ms !important;
  }
}
</style>

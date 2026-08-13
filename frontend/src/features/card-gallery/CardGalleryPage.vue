<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="Images"
      :title="`${cardPoolLabel(workspace.activePool)} Gallery`"
      :subtitle="gallerySubtitle"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <AppHeaderAction
          v-if="workspace.activePool === 'player'"
          :icon="Hammer"
          label="Build a deck"
          short-label="Build a deck"
          variant="primary"
          :to="newDeckLocation"
        />
      </template>
    </AppPageHeader>

    <AppPageLayout>
      <template #aside>
        <GalleryFilterSidebar
          title="Gallery"
          description="Search cards by name, type line, rules text, or cost, then refine by symbols, stats, and metadata."
          :query="query"
          :on-update-query="updateQuery"
          search-placeholder="Search by name, type, rules, or cost..."
          :total-count="totalCount"
          :on-reset="resetFilters"
        >
          <CardFilterSections
            :state="filterSectionsState"
            :show-card-pool="false"
          />

          <template #footer>
            <div class="flex w-full flex-col gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <CardSortMenu
                  :sort="effectiveSort"
                  :default-sort="defaultSort"
                  :override-active="gallerySortOverride !== null"
                  allow-default-option
                  @update:sort="setGallerySortOverride"
                  @reset="clearGallerySortOverride"
                />
                <GalleryOptionsMenu
                  :hover-mode="effectiveHoverMode"
                  :default-hover-mode="defaultHoverMode"
                  :hover-mode-override-active="galleryHoverModeOverride !== null"
                  allow-hover-mode-default-option
                  :card-scale="cardScale"
                  :show-card-groups="showCardGroups"
                  :page-size="pageSize"
                  show-page-size-control
                  @update:hover-mode="setGalleryHoverModeOverride"
                  @reset:hover-mode="clearGalleryHoverModeOverride"
                  @update:card-scale="cardScale = $event"
                  @update:show-card-groups="showCardGroups = $event"
                  @update:page-size="pageSize = $event"
                />
              </div>
              <div
                v-if="auth.canAccessStaffRoutes"
                class="flex flex-wrap gap-2"
              >
                <button
                  class="btn-secondary inline-flex w-fit items-center gap-2 whitespace-nowrap"
                  type="button"
                  :disabled="isExportingTtsCards || !exportsReady"
                  @click="exportTtsCards"
                >
                  <Copy class="h-4 w-4" />
                  <span>{{ isExportingTtsCards ? 'Exporting...' : 'Export TTS Cards' }}</span>
                </button>
                <button
                  class="btn-secondary inline-flex w-fit items-center gap-2 whitespace-nowrap"
                  type="button"
                  :disabled="!exportsReady"
                  @click="exportCsv"
                >
                  <Download class="h-4 w-4" />
                  <span>Export CSV</span>
                </button>
              </div>
            </div>
          </template>
        </GalleryFilterSidebar>
      </template>

      <div class="space-y-6">
        <div
          class="grid gap-6"
          :style="galleryGridStyle"
        >
          <CardGalleryItem
            v-for="card in displayItems"
            :key="`${card.result_type}:${card.id}`"
            :card="card"
            :hover-mode="effectiveHoverMode"
            :card-height-rem="cardHeightRem"
          >
            <template
              v-if="auth.canAccessStaffRoutes"
              #hover-actions="{ cardItem, isCard, editLocation }"
            >
              <RouterLink
                v-if="isCard && cardItem"
                :to="editLocation"
                class="btn-secondary pointer-events-auto gap-1.5 rounded-full px-3 py-1.5 text-xs shadow-xl"
              >
                <Pencil class="h-3.5 w-3.5" />
                <span>Edit</span>
              </RouterLink>
            </template>
          </CardGalleryItem>
        </div>

        <div
          v-if="hasLoadedOnce && !isRefreshing && cards.length > 0"
          ref="loadMoreSentinelRef"
          class="theme-section-muted flex justify-center py-4 text-sm"
        >
          <span v-if="isLoadingPage">Loading more cards...</span>
          <span v-else-if="nextPage === null">All cards loaded.</span>
          <span v-else>Scroll to load more.</span>
        </div>

        <div
          v-if="hasLoadedOnce && !isLoadingInitial && !isRefreshing && cards.length === 0"
          class="page-card theme-section-muted text-sm"
        >
          No cards found for the current filters.
        </div>
      </div>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { useScroll, useTimeoutFn } from '@vueuse/core';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Copy, Download, Hammer, Images, Pencil } from 'lucide-vue-next';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { useCsvExport } from '@/shared/composables/useCsvExport';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import { createLoadingShimItems } from '@/domain/cards/utils/galleryDisplayItems';
import { useScrollContainer } from '@/shared/composables/useScrollContainer';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import CardGalleryItem from '@/domain/cards/components/CardGalleryItem.vue';
import CardSortMenu from '@/domain/cards/components/CardSortMenu.vue';
import GalleryOptionsMenu from '@/domain/cards/components/GalleryOptionsMenu.vue';
import { useAuthStore } from '@/domain/session/store';
import type { GalleryItem } from '@/domain/cards/types';
import {
  createEmptyCardFilterState,
} from '@/domain/cards/utils/filters/cardFilterState';
import {
  buildCardFilterApiPayload,
  buildCardFilterApiSearchParams,
} from '@/domain/cards/utils/filters/cardFilterRequest';
import {
  buildCardFilterRouteQuery,
  getCardFilterSignature,
  isCardFilterStateReady,
  parseCardFilterRouteQuery,
  sameCardFilterState,
} from '@/domain/cards/utils/filters/cardFilterRouteState';
import { useCardFilterController } from '@/domain/cards/composables/filters/useCardFilterController';
import {
  getGallerySnapshot,
  saveGallerySnapshot,
  setGalleryNavigationCards,
} from '@/domain/cards/utils/gallery/galleryNavigation';
import { appendCardSortSearchParam } from '@/domain/cards/utils/gallery/cardSort';
import { useCardSortSurface } from '@/domain/cards/composables/useCardSortPreferences';
import CardFilterSections from '@/domain/cards/components/filters/CardFilterSections.vue';
import GalleryFilterSidebar from '@/domain/cards/components/filters/GalleryFilterSidebar.vue';
import { useCardCollection } from '@/domain/cards/composables/useCardCollection';
import { useGalleryOptions } from '@/domain/cards/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/domain/cards/composables/useHoverModePreferences';
import { useTtsCardExport } from '@/domain/cards/composables/useTtsCardExport';
import { buildContextualNewDeckEditorLocation } from '@/domain/decks/utils/deckRouteState';
import { cardPoolLabel } from '@/domain/cards/cardPools';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const workspace = useCardPoolWorkspaceStore();
const scrollContainer = useScrollContainer();
const { y: scrollTopRef } = useScroll(scrollContainer);

const filterController = useCardFilterController({
  resultSetKey: computed(() => workspace.generation),
});
const {
  query,
  filterSectionsState,
  filtersLoaded,
  selectionState,
  readFilterState,
  applyRouteFilterState,
  updateQuery,
  loadFilters,
} = filterController;
const currentRouteFilterState = computed(() => parseCardFilterRouteQuery(route.query));
const currentRouteSignature = computed(() => getCardFilterSignature(currentRouteFilterState.value));
const loadMoreSentinelRef = ref<HTMLElement | null>(null);
const { exportCardsCsv } = useCsvExport();
const { copyTtsCardExport, isExportingTtsCards } = useTtsCardExport();
const { cardScale, showCardGroups, pageSize } = useGalleryOptions();
const { defaultSort, overrideSort, effectiveSort, setOverrideSort, clearOverrideSort } = useCardSortSurface('gallery');
const {
  defaultHoverMode,
  overrideHoverMode: galleryHoverModeOverride,
  effectiveHoverMode,
  setOverrideHoverMode,
  clearOverrideHoverMode,
} = useHoverModeSurface('gallery');
const collection = useCardCollection<GalleryItem>({
  buildSearchParams: () => {
    const params = buildCardFilterApiSearchParams(selectionState.value);
    if (showCardGroups.value) {
      params.set('show_groups', 'true');
    }
    return appendCardSortSearchParam(params, effectiveSort.value);
  },
  filtersLoaded,
  pageSize,
  identity: (card) => `${card.result_type}:${card.id}`,
  resultSetKey: computed(() => workspace.generation),
  refreshOnResultSetChange: false,
});
const cards = collection.cards;
const totalCount = collection.totalCount;
const nextPage = collection.nextPage;
const isLoadingInitial = collection.isLoadingInitial;
const isRefreshing = collection.isRefreshing;
const isLoadingPage = collection.isLoadingPage;
const hasLoadedOnce = collection.hasLoadedOnce;
const cardHeightRem = computed(() => Number((27 * cardScale.value).toFixed(2)));
const galleryGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(290 * cardScale.value)}px, 1fr))`,
}));
const gallerySortOverride = computed(() => overrideSort.value);
const newDeckLocation = computed(() => buildContextualNewDeckEditorLocation(route.path, route.query));
const gallerySubtitle = computed(() =>
  workspace.activePool === 'player'
    ? 'Browse Player cards and find cards to build around.'
    : `Browse ${cardPoolLabel(workspace.activePool)} cards.`,
);
const loadingShimCount = computed(() => pageSize.value);
const displayItems = computed(() =>
  (!hasLoadedOnce.value || isRefreshing.value)
    ? createLoadingShimItems(loadingShimCount.value)
    : cards.value,
);
const exportsReady = computed(() => isCardFilterStateReady(
  filtersLoaded.value,
  readFilterState(),
  currentRouteFilterState.value,
));
let componentActive = true;

const captureExportRequestGuard = (): (() => boolean) => {
  const expectedGeneration = workspace.generation;
  return () => componentActive && workspace.generation === expectedGeneration;
};

const restoreScroll = (value: number): void => {
  window.requestAnimationFrame(() => {
    scrollTopRef.value = value;
  });
};

const exportCsv = async (): Promise<void> => {
  if (!exportsReady.value) {
    return;
  }
  const isRequestCurrent = captureExportRequestGuard();
  const params = buildCardFilterApiSearchParams(selectionState.value);
  await exportCardsCsv(
    appendCardSortSearchParam(params, effectiveSort.value),
    isRequestCurrent,
  );
};

const exportTtsCards = async (): Promise<void> => {
  if (!exportsReady.value) {
    return;
  }
  const isRequestCurrent = captureExportRequestGuard();
  await copyTtsCardExport({
    type: 'gallery',
    filters: {
      ...buildCardFilterApiPayload(selectionState.value),
      sort: effectiveSort.value,
    },
  }, isRequestCurrent);
};

const setGallerySortOverride = (value: typeof effectiveSort.value): void => {
  setOverrideSort(value);
};

const clearGallerySortOverride = (): void => {
  clearOverrideSort();
};

const setGalleryHoverModeOverride = (value: typeof effectiveHoverMode.value): void => {
  setOverrideHoverMode(value);
};

const clearGalleryHoverModeOverride = (): void => {
  clearOverrideHoverMode();
};

const updateFilterRoute = (): void => {
  if (!filtersLoaded.value) {
    return;
  }
  const nextRouteState = readFilterState();
  if (sameCardFilterState(nextRouteState, currentRouteFilterState.value)) {
    return;
  }
  void router.replace({
    path: '/cards',
    query: buildCardFilterRouteQuery(nextRouteState),
  });
};
const {
  start: debouncedUpdateRoute,
  stop: cancelDebouncedUpdateRoute,
} = useTimeoutFn(updateFilterRoute, 250, { immediate: false });

const observedFilterState = computed(() => selectionState.value);
const galleryNavigationSearchParams = computed(() => {
  const params = buildCardFilterApiSearchParams(selectionState.value);
  if (showCardGroups.value) {
    params.set('show_groups', 'true');
  }
  appendCardSortSearchParam(params, effectiveSort.value);
  return params.toString();
});
const galleryRequestSignature = computed(
  () => `${currentRouteSignature.value}::${showCardGroups.value ? 'groups' : 'cards'}::${effectiveSort.value}::${pageSize.value}`,
);

watch(
  observedFilterState,
  () => {
    debouncedUpdateRoute();
  },
  { deep: true },
);

watch(
  () => workspace.generation,
  () => {
    cancelDebouncedUpdateRoute();
  },
  { flush: 'sync' },
);

watch(
  loadMoreSentinelRef,
  (element) => {
    collection.setLoadMoreSentinel(element);
  },
  { immediate: true },
);

watch(
  () => ({
    cards: cards.value.map((card) => ({ id: card.id, result_type: card.result_type })),
    totalCount: totalCount.value,
    nextPage: nextPage.value,
    pageSize: collection.galleryState.value.pageSize,
    searchParams: galleryNavigationSearchParams.value,
  }),
  ({ cards, totalCount, nextPage, pageSize, searchParams }) => {
    setGalleryNavigationCards(cards, totalCount, nextPage, pageSize, searchParams);
  },
  { immediate: true },
);

watch(
  [galleryRequestSignature, filtersLoaded],
  async ([searchParams, ready]) => {
    if (!ready) {
      return;
    }

    const routeState = currentRouteFilterState.value;
    if (!sameCardFilterState(readFilterState(), routeState)) {
      applyRouteFilterState(routeState);
    }

    const snapshot = getGallerySnapshot<GalleryItem>(searchParams);
    if (snapshot) {
      collection.galleryState.value = snapshot.pageState;
      isLoadingInitial.value = false;
      isRefreshing.value = false;
      isLoadingPage.value = false;
      collection.hasLoadedOnce.value = true;
      saveGallerySnapshot(searchParams, snapshot.pageState, snapshot.scrollTop);
      await nextTick();
      restoreScroll(snapshot.scrollTop);
      return;
    }

    scrollTopRef.value = 0;
    await collection.searchCards();
    saveGallerySnapshot(searchParams, collection.galleryState.value, scrollTopRef.value);
  },
  { immediate: true },
);

const resetFilters = (): void => {
  const defaults = createEmptyCardFilterState(workspace.activePool);
  applyRouteFilterState(defaults);
  void router.replace({ path: '/cards', query: buildCardFilterRouteQuery(defaults) });
};

onBeforeRouteLeave(() => {
  saveGallerySnapshot(galleryRequestSignature.value, collection.galleryState.value, scrollTopRef.value);
});

onBeforeUnmount(() => {
  componentActive = false;
  cancelDebouncedUpdateRoute();
});

onMounted(() => {
  void loadFilters();
});
</script>

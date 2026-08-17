<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="CARD_POOL_ICONS[workspace.activePool]"
      :title="`${cardPoolLabel(workspace.activePool)} Gallery`"
      :subtitle="gallerySubtitle"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <AppHeaderAction
          v-if="workspace.activePool === 'player'"
          :icon="APP_SECTION_ICONS.deckBuilder"
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
            :visible-sections="visibleFilterSections"
          />
          <div
            v-if="filtersError"
            class="theme-section-muted space-y-2 text-xs"
            role="status"
          >
            <p>Filter options could not be loaded. Card browsing is still available.</p>
            <button
              class="btn-secondary"
              type="button"
              @click="retryFilterLoad"
            >
              Retry filter options
            </button>
          </div>

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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import { Copy, Download, Pencil } from 'lucide-vue-next';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { useCsvExport } from '@/shared/composables/useCsvExport';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import { createLoadingShimItems } from '@/domain/cards/utils/galleryDisplayItems';
import { useScrollContainer } from '@/shared/composables/useScrollContainer';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';
import CardGalleryItem from '@/domain/cards/components/CardGalleryItem.vue';
import CardSortMenu from '@/domain/cards/components/CardSortMenu.vue';
import GalleryOptionsMenu from '@/domain/cards/components/GalleryOptionsMenu.vue';
import { useAuthStore } from '@/domain/session/store';
import type { GalleryItem } from '@/domain/cards/types';
import {
  createEmptyCardFilterState,
  type CardFilterState,
} from '@/domain/cards/utils/filters/cardFilterState';
import {
  getGalleryVisibleFilterSections,
  sanitizeGalleryFilterStateForPool,
} from '@/domain/cards/utils/filters/cardGalleryFacetPolicy';
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
  cardFilterStateRequiresCatalog,
  reconcileCardFilterStateWithCatalog,
} from '@/domain/cards/utils/filters/cardFilterSelection';
import {
  getGallerySnapshot,
  clearGalleryNavigationState,
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
import { CARD_POOL_ICONS } from '@/domain/cards/cardPoolIcons';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const workspace = useCardPoolWorkspaceStore();
const scrollContainer = useScrollContainer();
const { y: scrollTopRef } = useScroll(scrollContainer);

const filterController = useCardFilterController({
  resultSetKey: computed(() => workspace.generation),
  cardPool: computed(() => workspace.activePool),
});
const {
  query,
  filterSectionsState,
  filtersLoaded,
  filtersError,
  filterCatalog,
  selectionState,
  readFilterState,
  applyRouteFilterState,
  updateQuery,
  loadFilters,
} = filterController;
const parsedRouteFilterState = computed(() => parseCardFilterRouteQuery(route.query));
const visibleRouteFilterState = computed(() =>
  sanitizeGalleryFilterStateForPool(parsedRouteFilterState.value, workspace.activePool),
);
const currentRouteFilterState = computed(() => (
  filtersLoaded.value
    ? reconcileCardFilterStateWithCatalog(visibleRouteFilterState.value, filterCatalog.value)
    : visibleRouteFilterState.value
));
const currentRouteSignature = computed(() => getCardFilterSignature(currentRouteFilterState.value));
const pendingFilterRouteState = shallowRef<CardFilterState | null>(null);
let pendingFilterRouteDebounceElapsed = false;
let observedFilterStateSnapshot = sanitizeGalleryFilterStateForPool(
  readFilterState(),
  workspace.activePool,
);
const filterRouteUpdatePending = computed(() => pendingFilterRouteState.value !== null);
const visibleFilterSections = computed(() =>
  getGalleryVisibleFilterSections(workspace.activePool),
);
const canonicalRouteQuery = computed(() =>
  buildCardFilterRouteQuery(currentRouteFilterState.value),
);
const canonicalRouteFullPath = computed(() =>
  router.resolve({ path: '/cards', query: canonicalRouteQuery.value }).fullPath,
);
const loadMoreSentinelRef = ref<HTMLElement | null>(null);
const { exportCardsCsv } = useCsvExport();
const {
  copyTtsCardExport,
  invalidateTtsCardExport,
  isExportingTtsCards,
} = useTtsCardExport();
const { cardScale, showCardGroups, pageSize } = useGalleryOptions();
const { defaultSort, overrideSort, effectiveSort, setOverrideSort, clearOverrideSort } = useCardSortSurface('gallery');
const {
  defaultHoverMode,
  overrideHoverMode: galleryHoverModeOverride,
  effectiveHoverMode,
  setOverrideHoverMode,
  clearOverrideHoverMode,
} = useHoverModeSurface('gallery');
const isFilterStateReadyForCatalogStatus = (state: CardFilterState): boolean => (
  filtersLoaded.value
  || (
    filtersError.value !== null
    && !cardFilterStateRequiresCatalog(state)
  )
);
const cardCollectionFiltersReady = computed(
  () => isFilterStateReadyForCatalogStatus(visibleRouteFilterState.value),
);
const collection = useCardCollection<GalleryItem>({
  buildSearchParams: () => {
    const params = buildCardFilterApiSearchParams(selectionState.value);
    if (showCardGroups.value) {
      params.set('show_groups', 'true');
    }
    return appendCardSortSearchParam(params, effectiveSort.value);
  },
  filtersLoaded: cardCollectionFiltersReady,
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

const filterStateValueEquals = (
  left: CardFilterState[keyof CardFilterState],
  right: CardFilterState[keyof CardFilterState],
): boolean => (
  Array.isArray(left) && Array.isArray(right)
    ? left.length === right.length && left.every((value, index) => value === right[index])
    : left === right
);

const mergeChangedFilterState = (
  baseState: CardFilterState,
  previousState: CardFilterState,
  nextState: CardFilterState,
): CardFilterState => {
  const mergedState = { ...baseState };
  (Object.keys(nextState) as (keyof CardFilterState)[]).forEach((key) => {
    const nextValue = nextState[key];
    if (!filterStateValueEquals(previousState[key], nextValue)) {
      Object.assign(mergedState, {
        [key]: Array.isArray(nextValue) ? [...nextValue] : nextValue,
      });
    }
  });
  return mergedState;
};

const applyPendingFilterRoute = (nextRouteState: CardFilterState): void => {
  if (!isFilterStateReadyForCatalogStatus(nextRouteState)) {
    return;
  }
  void router.replace({
    path: '/cards',
    query: buildCardFilterRouteQuery(nextRouteState),
  }).finally(() => {
    if (pendingFilterRouteState.value === nextRouteState) {
      pendingFilterRouteState.value = null;
    }
  });
};

const capturePendingFilterRoute = (): CardFilterState | null => {
  const nextFilterState = sanitizeGalleryFilterStateForPool(
    readFilterState(),
    workspace.activePool,
  );
  if (sameCardFilterState(nextFilterState, observedFilterStateSnapshot)) {
    return pendingFilterRouteState.value;
  }
  const baseState = pendingFilterRouteState.value ?? visibleRouteFilterState.value;
  const nextRouteState = pendingFilterRouteState.value !== null
    || (!filtersLoaded.value && cardFilterStateRequiresCatalog(visibleRouteFilterState.value))
    ? mergeChangedFilterState(baseState, observedFilterStateSnapshot, nextFilterState)
    : nextFilterState;
  observedFilterStateSnapshot = nextFilterState;
  if (sameCardFilterState(nextRouteState, currentRouteFilterState.value)) {
    pendingFilterRouteState.value = null;
    pendingFilterRouteDebounceElapsed = false;
    return null;
  }
  pendingFilterRouteState.value = nextRouteState;
  pendingFilterRouteDebounceElapsed = false;
  return nextRouteState;
};

const flushPendingFilterRoute = (): void => {
  const pendingState = pendingFilterRouteState.value;
  if (!pendingState) {
    return;
  }
  pendingFilterRouteDebounceElapsed = true;
  applyPendingFilterRoute(pendingState);
};
const {
  start: debouncedUpdateRoute,
  stop: cancelDebouncedUpdateRoute,
} = useTimeoutFn(flushPendingFilterRoute, 250, { immediate: false });

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
  () => `${filtersLoaded.value ? 'catalog' : 'fallback'}::${currentRouteSignature.value}::${showCardGroups.value ? 'groups' : 'cards'}::${effectiveSort.value}::${pageSize.value}`,
);

watch(
  observedFilterState,
  () => {
    const nextFilterState = sanitizeGalleryFilterStateForPool(
      readFilterState(),
      workspace.activePool,
    );
    if (sameCardFilterState(nextFilterState, observedFilterStateSnapshot)) {
      return;
    }
    cancelDebouncedUpdateRoute();
    if (capturePendingFilterRoute()) {
      debouncedUpdateRoute();
    }
  },
  { deep: true },
);

watch(
  [filtersLoaded, filtersError],
  () => {
    const pendingState = pendingFilterRouteState.value;
    if (
      pendingState
      && pendingFilterRouteDebounceElapsed
      && isFilterStateReadyForCatalogStatus(pendingState)
    ) {
      applyPendingFilterRoute(pendingState);
    }
  },
  { flush: 'sync' },
);

watch(
  () => route.fullPath,
  (fullPath) => {
    const pendingState = pendingFilterRouteState.value;
    if (!pendingState) {
      return;
    }
    const pendingFullPath = router.resolve({
      path: '/cards',
      query: buildCardFilterRouteQuery(pendingState),
    }).fullPath;
    if (fullPath === pendingFullPath) {
      return;
    }
    cancelDebouncedUpdateRoute();
    pendingFilterRouteState.value = null;
    pendingFilterRouteDebounceElapsed = false;
  },
  { flush: 'sync' },
);

watch(
  () => workspace.generation,
  () => {
    cancelDebouncedUpdateRoute();
    pendingFilterRouteState.value = null;
    pendingFilterRouteDebounceElapsed = false;
    observedFilterStateSnapshot = sanitizeGalleryFilterStateForPool(
      readFilterState(),
      workspace.activePool,
    );
    invalidateTtsCardExport();
    clearGalleryNavigationState();
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
  [
    galleryRequestSignature,
    cardCollectionFiltersReady,
    () => route.fullPath,
    filterRouteUpdatePending,
  ],
  async ([searchParams, ready, , routeUpdatePending]) => {
    const routeState = currentRouteFilterState.value;
    if (
      (ready || filtersError.value !== null)
      && !routeUpdatePending
      && !sameCardFilterState(readFilterState(), routeState)
    ) {
      applyRouteFilterState(routeState);
      observedFilterStateSnapshot = sanitizeGalleryFilterStateForPool(
        readFilterState(),
        workspace.activePool,
      );
    }

    if (!ready || routeUpdatePending) {
      return;
    }

    collection.invalidatePendingLoads();
    if (route.fullPath !== canonicalRouteFullPath.value) {
      await router.replace({ path: '/cards', query: canonicalRouteQuery.value });
      return;
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
    const requestApplied = await collection.searchCards();
    if (!requestApplied) {
      return;
    }
    saveGallerySnapshot(searchParams, collection.galleryState.value, scrollTopRef.value);
  },
  { immediate: true },
);

const resetFilters = (): void => {
  cancelDebouncedUpdateRoute();
  pendingFilterRouteState.value = null;
  pendingFilterRouteDebounceElapsed = false;
  const defaults = sanitizeGalleryFilterStateForPool(
    createEmptyCardFilterState(workspace.activePool),
    workspace.activePool,
  );
  applyRouteFilterState(defaults);
  observedFilterStateSnapshot = defaults;
  void router.replace({ path: '/cards', query: buildCardFilterRouteQuery(defaults) });
};

const retryFilterLoad = (): void => {
  cancelDebouncedUpdateRoute();
  capturePendingFilterRoute();
  flushPendingFilterRoute();
  void loadFilters().catch(() => undefined);
};

onBeforeRouteLeave(() => {
  saveGallerySnapshot(galleryRequestSignature.value, collection.galleryState.value, scrollTopRef.value);
});

onBeforeUnmount(() => {
  componentActive = false;
  cancelDebouncedUpdateRoute();
});

onMounted(() => {
  void loadFilters().catch(() => undefined);
});
</script>

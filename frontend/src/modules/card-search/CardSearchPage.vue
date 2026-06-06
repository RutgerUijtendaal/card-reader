<template>
  <section class="grid gap-6 xl:grid-cols-[23rem_minmax(0,1fr)] xl:items-start">
    <GalleryFilterSidebar
      title="Gallery"
      description="Filter the visible card pool by symbols, stats, and metadata."
      :query="query"
      :on-update-query="updateQuery"
      search-placeholder="Search cards..."
      :total-count="totalCount"
      :on-reset="resetFilters"
    >
      <CardFilterSections :state="filterSectionsState" />

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
          <button
            v-if="auth.canAccessStaffRoutes"
            class="btn-secondary inline-flex w-fit items-center gap-2 whitespace-nowrap"
            type="button"
            @click="exportCsv"
          >
            <Download class="h-4 w-4" />
            <span>Export CSV</span>
          </button>
        </div>
      </template>
    </GalleryFilterSidebar>

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
  </section>
</template>

<script setup lang="ts">
import { useDebounceFn, useScroll } from '@vueuse/core';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { Download, Pencil } from 'lucide-vue-next';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { useCsvExport } from '@/composables/useCsvExport';
import { createLoadingShimItems } from '@/components/cards/galleryDisplayItems';
import { useScrollContainer } from '@/composables/useScrollContainer';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import CardSortMenu from '@/components/cards/CardSortMenu.vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import type { GalleryItem } from '@/modules/card-detail/types';
import {
  buildCardFilterApiSearchParams,
  buildCardFilterRouteQuery,
  createEmptyCardFilterState,
  getCardFilterSignature,
  parseCardFilterRouteQuery,
  sameCardFilterState,
} from '@/composables/card-filters/cardFilterState';
import { useCardFilterController } from '@/composables/card-filters/useCardFilterController';
import {
  getGallerySnapshot,
  saveGallerySnapshot,
  setGalleryNavigationCards,
} from '@/composables/card-gallery/galleryNavigation';
import { appendCardSortSearchParam } from '@/composables/card-gallery/cardSort';
import { useCardSortSurface } from '@/composables/useCardSortPreferences';
import CardFilterSections from '@/components/filters/CardFilterSections.vue';
import GalleryFilterSidebar from '@/components/filters/GalleryFilterSidebar.vue';
import { useCardCollection } from '@/composables/useCardCollection';
import { useGalleryOptions } from '@/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/composables/useHoverModePreferences';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const scrollContainer = useScrollContainer();
const { y: scrollTopRef } = useScroll(scrollContainer);

const filterController = useCardFilterController();
const {
  query,
  filterSectionsState,
  filtersLoaded,
  selectionState,
  readFilterState,
  applyRouteFilterState,
  resetFilters: resetCardFilterState,
  updateQuery,
  loadFilters,
} = filterController;
const currentRouteFilterState = computed(() => parseCardFilterRouteQuery(route.query));
const currentRouteSignature = computed(() => getCardFilterSignature(currentRouteFilterState.value));
const loadMoreSentinelRef = ref<HTMLElement | null>(null);
const { exportCardsCsv } = useCsvExport();
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
const loadingShimCount = computed(() => pageSize.value);
const displayItems = computed(() =>
  (!hasLoadedOnce.value || isRefreshing.value)
    ? createLoadingShimItems(loadingShimCount.value)
    : cards.value,
);

const restoreScroll = (value: number): void => {
  window.requestAnimationFrame(() => {
    scrollTopRef.value = value;
  });
};

const exportCsv = async (): Promise<void> => {
  const params = buildCardFilterApiSearchParams(selectionState.value);
  await exportCardsCsv(appendCardSortSearchParam(params, effectiveSort.value));
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

const debouncedUpdateRoute = useDebounceFn(() => {
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
}, 250);

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
  resetCardFilterState();
  void router.replace({ path: '/cards', query: buildCardFilterRouteQuery(createEmptyCardFilterState()) });
};

onBeforeRouteLeave(() => {
  saveGallerySnapshot(galleryRequestSignature.value, collection.galleryState.value, scrollTopRef.value);
});

onMounted(() => {
  void loadFilters();
});
</script>

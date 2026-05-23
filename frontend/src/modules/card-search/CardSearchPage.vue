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
        <GalleryOptionsMenu
          :tooltip-enabled="tooltipEnabled"
          :card-scale="cardScale"
          :show-card-groups="showCardGroups"
          @update:tooltip-enabled="tooltipEnabled = $event"
          @update:card-scale="cardScale = $event"
          @update:show-card-groups="showCardGroups = $event"
        />
        <button
          class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap"
          type="button"
          @click="exportCsv"
        >
          <Download class="h-4 w-4" />
          <span>Export CSV</span>
        </button>
      </template>
    </GalleryFilterSidebar>

    <div class="space-y-6">
      <div
        class="grid gap-6"
        :style="galleryGridStyle"
      >
        <CardGalleryItem
          v-for="card in cards"
          :key="card.id"
          :card="card"
          :tooltip-enabled="tooltipEnabled"
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
        v-if="cards.length > 0"
        ref="loadMoreSentinelRef"
        class="theme-section-muted flex justify-center py-4 text-sm"
      >
        <span v-if="isLoadingPage">Loading more cards...</span>
        <span v-else-if="nextPage === null">All cards loaded.</span>
        <span v-else>Scroll to load more.</span>
      </div>

      <div
        v-if="!isLoadingInitial && cards.length === 0"
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
import { useScrollContainer } from '@/composables/useScrollContainer';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
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
} from '@/modules/card-filters/cardFilterState';
import { useCardFilterController } from '@/modules/card-filters/useCardFilterController';
import {
  getGallerySnapshot,
  saveGallerySnapshot,
  setGalleryNavigationCards,
} from '@/modules/card-search/galleryNavigation';
import CardFilterSections from '@/modules/card-search/components/CardFilterSections.vue';
import GalleryFilterSidebar from '@/modules/card-search/components/GalleryFilterSidebar.vue';
import { useCardCollection } from '@/modules/card-search/useCardCollection';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';

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
const { tooltipEnabled, cardScale, showCardGroups } = useGalleryOptions();
const collection = useCardCollection<GalleryItem>({
  buildSearchParams: () => {
    const params = buildCardFilterApiSearchParams(selectionState.value);
    if (showCardGroups.value) {
      params.set('show_groups', 'true');
    }
    return params;
  },
  filtersLoaded,
  pageSize: 72,
  identity: (card) => `${card.result_type}:${card.id}`,
});
const cards = collection.cards;
const totalCount = collection.totalCount;
const nextPage = collection.nextPage;
const isLoadingInitial = collection.isLoadingInitial;
const isLoadingPage = collection.isLoadingPage;
const cardHeightRem = computed(() => Number((27 * cardScale.value).toFixed(2)));
const galleryGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(290 * cardScale.value)}px, 1fr))`,
}));

const restoreScroll = (value: number): void => {
  window.requestAnimationFrame(() => {
    scrollTopRef.value = value;
  });
};

const exportCsv = async (): Promise<void> => {
  await exportCardsCsv(buildCardFilterApiSearchParams(selectionState.value));
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
  return params.toString();
});
const galleryRequestSignature = computed(
  () => `${currentRouteSignature.value}::${showCardGroups.value ? 'groups' : 'cards'}`,
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
      isLoadingPage.value = false;
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

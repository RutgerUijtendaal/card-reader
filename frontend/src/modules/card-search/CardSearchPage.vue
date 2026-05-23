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
        />
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
import { useDebounceFn, useIntersectionObserver, useScroll } from '@vueuse/core';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { Download } from 'lucide-vue-next';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { api } from '@/api/client';
import { useCsvExport } from '@/composables/useCsvExport';
import { useScrollContainer } from '@/composables/useScrollContainer';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import type {
  CardFiltersResponse,
  GalleryItem,
  PaginatedCardsResponse,
} from '@/modules/card-detail/types';
import {
  buildCardFilterApiSearchParams,
  buildCardFilterRouteQuery,
  createCardFilterCatalog,
  createEmptyCardFilterState,
  getCardFilterSignature,
  parseCardFilterRouteQuery,
  sameCardFilterState,
} from '@/modules/card-filters/cardFilterState';
import { useCardFilterState } from '@/modules/card-filters/useCardFilterState';
import {
  appendGalleryPage,
  createEmptyGalleryPageState,
  isLatestGalleryRequest,
  replaceGalleryPage,
} from '@/modules/card-search/galleryState';
import {
  getGallerySnapshot,
  saveGallerySnapshot,
  setGalleryNavigationCards,
} from '@/modules/card-search/galleryNavigation';
import CardFilterSections, { type CardFilterSectionsState } from '@/modules/card-search/components/CardFilterSections.vue';
import GalleryFilterSidebar from '@/modules/card-search/components/GalleryFilterSidebar.vue';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';

const route = useRoute();
const router = useRouter();
const scrollContainer = useScrollContainer();
const { y: scrollTopRef } = useScroll(scrollContainer);

const filters = ref<CardFiltersResponse>({
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
});
const filterCatalog = computed(() => createCardFilterCatalog(filters.value));
const {
  query,
  keywordMatch,
  tagMatch,
  typeMatch,
  manaCostMin,
  manaCostMax,
  manaSymbolMatch,
  affinitySymbolMatch,
  devotionSymbolMatch,
  otherSymbolMatch,
  attackMin,
  attackMax,
  healthMin,
  healthMax,
  keywordIds: selectedKeywordIds,
  tagIds: selectedTagIds,
  manaTypeSymbolIds: selectedManaTypeSymbolIds,
  affinitySymbolIds: selectedAffinitySymbolIds,
  devotionSymbolIds: selectedDevotionSymbolIds,
  otherSymbolIds: selectedOtherSymbolIds,
  typeIds: selectedTypeIds,
  selectionState,
  applyFilterState,
  readFilterState,
  reset: resetCardFilterState,
} = useCardFilterState(filterCatalog);
const galleryState = ref(createEmptyGalleryPageState<GalleryItem>());
const cards = computed(() => galleryState.value.cards);
const totalCount = computed(() => galleryState.value.count);
const nextPage = computed(() => galleryState.value.nextPage);
const currentRouteFilterState = computed(() => parseCardFilterRouteQuery(route.query));
const currentRouteSignature = computed(() => getCardFilterSignature(currentRouteFilterState.value));
const filtersLoaded = ref(false);
const isLoadingInitial = ref(false);
const isLoadingPage = ref(false);
const loadMoreSentinelRef = ref<HTMLElement | null>(null);
let latestSearchRequestId = 0;
const { exportCardsCsv } = useCsvExport();
const { tooltipEnabled, cardScale, showCardGroups } = useGalleryOptions();
const manaTypeOptions = computed(() => filterCatalog.value.manaSymbols);
const affinityTypeOptions = computed(() => filterCatalog.value.affinitySymbols);
const devotionTypeOptions = computed(() => filterCatalog.value.devotionSymbols);
const otherSymbolOptions = computed(() => filterCatalog.value.otherSymbols);
const cardHeightRem = computed(() => Number((27 * cardScale.value).toFixed(2)));
const galleryGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(290 * cardScale.value)}px, 1fr))`,
}));
const updateQuery = (value: string): void => {
  query.value = value;
};
const filterSectionsState = computed<CardFilterSectionsState>(() => ({
  selectedManaTypeSymbolIds,
  manaSymbolMatch,
  manaTypeOptions: manaTypeOptions.value,
  manaCostMin,
  manaCostMax,
  resetManaGroup,
  selectedTypeIds,
  typeMatch,
  typeOptions: filters.value.types,
  resetTypeGroup,
  selectedAffinitySymbolIds,
  affinitySymbolMatch,
  affinityTypeOptions: affinityTypeOptions.value,
  resetAffinityGroup,
  selectedDevotionSymbolIds,
  devotionSymbolMatch,
  devotionTypeOptions: devotionTypeOptions.value,
  resetDevotionGroup,
  selectedOtherSymbolIds,
  otherSymbolMatch,
  otherSymbolOptions: otherSymbolOptions.value,
  resetGenericGroup,
  attackMin,
  attackMax,
  healthMin,
  healthMax,
  selectedKeywordIds,
  keywordMatch,
  keywordOptions: filters.value.keywords,
  resetKeywordGroup,
  selectedTagIds,
  tagMatch,
  tagOptions: filters.value.tags,
  resetTagGroup,
}));

const resetManaGroup = (): void => {
  selectedManaTypeSymbolIds.value = [];
  manaSymbolMatch.value = 'any';
  manaCostMin.value = '';
  manaCostMax.value = '';
};

const resetAffinityGroup = (): void => {
  selectedAffinitySymbolIds.value = [];
  affinitySymbolMatch.value = 'any';
};

const resetDevotionGroup = (): void => {
  selectedDevotionSymbolIds.value = [];
  devotionSymbolMatch.value = 'any';
};

const resetGenericGroup = (): void => {
  selectedOtherSymbolIds.value = [];
  otherSymbolMatch.value = 'any';
  attackMin.value = '';
  attackMax.value = '';
  healthMin.value = '';
  healthMax.value = '';
};

const resetKeywordGroup = (): void => {
  selectedKeywordIds.value = [];
  keywordMatch.value = 'any';
};

const resetTagGroup = (): void => {
  selectedTagIds.value = [];
  tagMatch.value = 'any';
};

const resetTypeGroup = (): void => {
  selectedTypeIds.value = [];
  typeMatch.value = 'any';
};

const loadFilters = async (): Promise<void> => {
  const response = await api.get<CardFiltersResponse>('/cards/filters');
  filters.value = response.data;
  filtersLoaded.value = true;
};

const restoreScroll = (value: number): void => {
  window.requestAnimationFrame(() => {
    scrollTopRef.value = value;
  });
};

const loadCardsPage = async (page: number, mode: 'replace' | 'append'): Promise<void> => {
  const requestId = ++latestSearchRequestId;
  const params = buildCardFilterApiSearchParams(selectionState.value);
  if (showCardGroups.value) {
    params.set('show_groups', 'true');
  }
  params.set('page', String(page));
  params.set('page_size', '72');
  if (mode === 'replace') {
    isLoadingInitial.value = true;
  } else {
    isLoadingPage.value = true;
  }

  try {
    const response = await api.get<PaginatedCardsResponse<GalleryItem>>(`/cards?${params.toString()}`);
    if (!isLatestGalleryRequest(requestId, latestSearchRequestId)) {
      return;
    }
    galleryState.value =
      mode === 'replace'
        ? replaceGalleryPage(response.data)
        : appendGalleryPage(galleryState.value, response.data);
  } finally {
    if (isLatestGalleryRequest(requestId, latestSearchRequestId)) {
      isLoadingInitial.value = false;
      isLoadingPage.value = false;
    }
  }
};

const searchCards = async (): Promise<void> => {
  galleryState.value = createEmptyGalleryPageState<GalleryItem>();
  await loadCardsPage(1, 'replace');
};

const loadNextPage = async (): Promise<void> => {
  if (isLoadingInitial.value || isLoadingPage.value || nextPage.value === null) {
    return;
  }
  await loadCardsPage(nextPage.value, 'append');
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

useIntersectionObserver(
  loadMoreSentinelRef,
  (entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      void loadNextPage();
    }
  },
  { rootMargin: '400px 0px' },
);

watch(
  () => ({
    cards: cards.value.map((card) => ({ id: card.id, result_type: card.result_type })),
    totalCount: totalCount.value,
    nextPage: nextPage.value,
    pageSize: galleryState.value.pageSize,
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
      applyFilterState(routeState);
    }

    const snapshot = getGallerySnapshot<GalleryItem>(searchParams);
    if (snapshot) {
      galleryState.value = snapshot.pageState;
      isLoadingInitial.value = false;
      isLoadingPage.value = false;
      saveGallerySnapshot(searchParams, snapshot.pageState, snapshot.scrollTop);
      await nextTick();
      restoreScroll(snapshot.scrollTop);
      return;
    }

    scrollTopRef.value = 0;
    await searchCards();
    saveGallerySnapshot(searchParams, galleryState.value, scrollTopRef.value);
  },
  { immediate: true },
);

const resetFilters = (): void => {
  resetCardFilterState();
  void router.replace({ path: '/cards', query: buildCardFilterRouteQuery(createEmptyCardFilterState()) });
};

onBeforeRouteLeave(() => {
  saveGallerySnapshot(galleryRequestSignature.value, galleryState.value, scrollTopRef.value);
});

onMounted(() => {
  void loadFilters();
});
</script>

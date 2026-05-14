<template>
  <section class="space-y-6">
    <div class="page-card sticky top-0 z-20 space-y-4">
      <h2 class="flex items-center gap-2 text-xl font-semibold text-slate-900">
        <Images class="h-5 w-5 text-slate-500" />
        <span>Card Gallery</span>
      </h2>

      <div class="grid grid-cols-1 gap-3 2xl:grid-cols-[minmax(0,1fr)_auto] 2xl:items-center">
        <div class="order-2 flex flex-wrap gap-2 2xl:order-1">
          <FilterMultiSelectPopover
            v-model="selectedKeywordIds"
            label="Keywords"
            :options="filters.keywords"
            empty-text="No keywords available."
          />
          <FilterMultiSelectPopover
            v-model="selectedTagIds"
            label="Tags"
            :options="filters.tags"
            empty-text="No tags available."
          />
          <FilterMultiSelectPopover
            v-model="selectedTypeIds"
            label="Types"
            :options="filters.types"
            empty-text="No types available."
          />
          <FilterMultiSelectPopover
            v-model="selectedManaTypeSymbolIds"
            label="Mana Type"
            :options="manaTypeOptions"
            empty-text="No mana symbols available."
          />
          <FilterMultiSelectPopover
            v-model="selectedAffinitySymbolIds"
            label="Affinity"
            :options="affinityTypeOptions"
            empty-text="No affinity symbols available."
          />
          <FilterMultiSelectPopover
            v-model="selectedDevotionSymbolIds"
            label="Devotion"
            :options="devotionTypeOptions"
            empty-text="No devotion symbols available."
          />
          <FilterMultiSelectPopover
            v-model="selectedOtherSymbolIds"
            label="Other Symbols"
            :options="otherSymbolOptions"
            empty-text="No non-mana symbols available."
          />
          <FilterTextPopover
            v-model="manaCost"
            label="Mana Cost"
            placeholder="e.g. 3"
          />
          <FilterTextPopover
            v-model="templateId"
            label="Template"
            placeholder="mtg-like-v1"
          />
          <FilterTextPopover
            v-model="attackMin"
            label="Attack ≥"
            input-type="number"
          />
          <FilterTextPopover
            v-model="attackMax"
            label="Attack ≤"
            input-type="number"
          />
          <FilterTextPopover
            v-model="healthMin"
            label="Health ≥"
            input-type="number"
          />
          <FilterTextPopover
            v-model="healthMax"
            label="Health ≤"
            input-type="number"
          />
        </div>

        <div
          class="order-1 flex min-w-0 flex-nowrap items-center gap-2 2xl:order-2 2xl:min-w-[26rem] 2xl:justify-end"
        >
          <input
            v-model="query"
            class="input-base min-w-[14rem] flex-1 2xl:w-80 2xl:flex-none"
            placeholder="Search cards..."
          >
          <span class="whitespace-nowrap text-xs text-slate-500">{{ totalCount }} results</span>
          <button
            class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap"
            type="button"
            @click="exportCsv"
          >
            <Download class="h-4 w-4" />
            <span>Export CSV</span>
          </button>
          <button
            class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap"
            type="button"
            @click="resetFilters"
          >
            <RotateCcw class="h-4 w-4" />
            <span>Reset</span>
          </button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-[repeat(auto-fill,minmax(290px,1fr))] gap-6 2xl:grid-cols-[repeat(auto-fill,minmax(340px,1fr))]">
      <CardGalleryItem
        v-for="card in cards"
        :key="card.id"
        :card="card"
      />
    </div>

    <div
      v-if="cards.length > 0"
      ref="loadMoreSentinelRef"
      class="flex justify-center py-4 text-sm text-slate-500"
    >
      <span v-if="isLoadingPage">Loading more cards...</span>
      <span v-else-if="nextPage === null">All cards loaded.</span>
      <span v-else>Scroll to load more.</span>
    </div>

    <div
      v-if="!isLoadingInitial && cards.length === 0"
      class="page-card text-sm text-slate-500"
    >
      No cards found for the current filters.
    </div>
  </section>
</template>

<script setup lang="ts">
import { useDebounceFn, useIntersectionObserver, useScroll } from '@vueuse/core';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { Download, Images, RotateCcw } from 'lucide-vue-next';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { api } from '@/api/client';
import { useCsvExport } from '@/composables/useCsvExport';
import { useScrollContainer } from '@/composables/useScrollContainer';
import FilterMultiSelectPopover from '@/components/filters/FilterMultiSelectPopover.vue';
import FilterTextPopover from '@/components/filters/FilterTextPopover.vue';
import CardGalleryItem, { type CardGalleryItemModel } from '@/components/cards/CardGalleryItem.vue';
import type {
  CardFiltersResponse,
  MetadataOption,
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
  manaCost,
  templateId,
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
const galleryState = ref(createEmptyGalleryPageState<CardGalleryItemModel>());
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
const manaTypeOptions = computed<MetadataOption[]>(() =>
  filterCatalog.value.manaSymbols,
);

const affinityTypeOptions = computed<MetadataOption[]>(() =>
  filterCatalog.value.affinitySymbols,
);

const devotionTypeOptions = computed<MetadataOption[]>(() =>
  filterCatalog.value.devotionSymbols,
);

const otherSymbolOptions = computed<MetadataOption[]>(() =>
  filterCatalog.value.otherSymbols,
);

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
  params.set('page', String(page));
  params.set('page_size', '72');
  if (mode === 'replace') {
    isLoadingInitial.value = true;
  } else {
    isLoadingPage.value = true;
  }

  try {
    const response = await api.get<PaginatedCardsResponse<CardGalleryItemModel>>(`/cards?${params.toString()}`);
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
  galleryState.value = createEmptyGalleryPageState<CardGalleryItemModel>();
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
const galleryNavigationSearchParams = computed(() =>
  buildCardFilterApiSearchParams(selectionState.value).toString(),
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
    cardIds: cards.value.map((card) => card.id),
    totalCount: totalCount.value,
    nextPage: nextPage.value,
    pageSize: galleryState.value.pageSize,
    searchParams: galleryNavigationSearchParams.value,
  }),
  ({ cardIds, totalCount, nextPage, pageSize, searchParams }) => {
    setGalleryNavigationCards(cardIds, totalCount, nextPage, pageSize, searchParams);
  },
  { immediate: true },
);

watch(
  [currentRouteSignature, filtersLoaded],
  async ([searchParams, ready]) => {
    if (!ready) {
      return;
    }

    const routeState = currentRouteFilterState.value;
    if (!sameCardFilterState(readFilterState(), routeState)) {
      applyFilterState(routeState);
    }

    const snapshot = getGallerySnapshot<CardGalleryItemModel>(searchParams);
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
  saveGallerySnapshot(currentRouteSignature.value, galleryState.value, scrollTopRef.value);
});

onMounted(() => {
  void loadFilters();
});
</script>

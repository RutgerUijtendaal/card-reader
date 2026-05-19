<template>
  <section class="grid gap-6 xl:grid-cols-[25rem_minmax(0,1fr)] xl:items-start">
    <aside class="page-card app-scrollbar space-y-4 xl:sticky xl:top-0 xl:h-[calc(100vh-2rem)] xl:overflow-y-auto">
      <div class="space-y-2">
        <h2 class="flex items-center gap-2 text-xl font-semibold text-slate-900">
          <Images class="h-5 w-5 text-slate-500" />
          <span>Card Gallery</span>
        </h2>
        <p class="text-sm text-slate-500">
          Filter the visible card pool by symbols, stats, and metadata.
        </p>
      </div>

      <div class="space-y-2">
        <input
          v-model="query"
          class="input-base"
          placeholder="Search cards..."
        >
        <p class="text-xs text-slate-500">
          {{ totalCount }} results
        </p>
      </div>

      <div class="space-y-3">
        <SymbolToggleGroup
          v-model="selectedManaTypeSymbolIds"
          v-model:match-mode="manaSymbolMatch"
          :default-open="true"
          label="Mana"
          :options="manaTypeOptions"
          @reset="resetManaGroup"
        >
          <div class="rounded-xl border border-slate-200 bg-white/80 p-3">
            <div class="flex items-center gap-3">
              <h4 class="w-16 shrink-0 text-sm font-semibold text-slate-900">
                Cost
              </h4>
              <div class="grid min-w-0 flex-1 grid-cols-2 gap-2">
                <input
                  v-model="manaCostMin"
                  class="input-base min-w-0"
                  type="number"
                  placeholder="Min"
                >
                <input
                  v-model="manaCostMax"
                  class="input-base min-w-0"
                  type="number"
                  placeholder="Max"
                >
              </div>
            </div>
          </div>
        </SymbolToggleGroup>
        <SymbolToggleGroup
          v-model="selectedAffinitySymbolIds"
          v-model:match-mode="affinitySymbolMatch"
          label="Affinity"
          :options="affinityTypeOptions"
          @reset="resetAffinityGroup"
        />
        <SymbolToggleGroup
          v-model="selectedDevotionSymbolIds"
          v-model:match-mode="devotionSymbolMatch"
          label="Devotion"
          :options="devotionTypeOptions"
          @reset="resetDevotionGroup"
        />
        <SymbolToggleGroup
          v-model="selectedOtherSymbolIds"
          v-model:match-mode="otherSymbolMatch"
          label="Generic"
          :options="otherSymbolOptions"
          @reset="resetGenericGroup"
        >
          <div class="space-y-2 rounded-xl border border-slate-200 bg-white/80 p-3">
            <div class="flex items-center gap-3">
              <h4 class="w-16 shrink-0 text-sm font-semibold text-slate-900">
                Attack
              </h4>
              <div class="grid min-w-0 flex-1 grid-cols-2 gap-2">
                <input
                  v-model="attackMin"
                  class="input-base min-w-0"
                  type="number"
                  placeholder="Min"
                >
                <input
                  v-model="attackMax"
                  class="input-base min-w-0"
                  type="number"
                  placeholder="Max"
                >
              </div>
            </div>

            <div class="flex items-center gap-3">
              <h4 class="w-16 shrink-0 text-sm font-semibold text-slate-900">
                Health
              </h4>
              <div class="grid min-w-0 flex-1 grid-cols-2 gap-2">
                <input
                  v-model="healthMin"
                  class="input-base min-w-0"
                  type="number"
                  placeholder="Min"
                >
                <input
                  v-model="healthMax"
                  class="input-base min-w-0"
                  type="number"
                  placeholder="Max"
                >
              </div>
            </div>
          </div>
        </SymbolToggleGroup>
      </div>

      <div class="space-y-3">
        <MetadataChecklistGroup
          v-model="selectedKeywordIds"
          v-model:match-mode="keywordMatch"
          label="Keywords"
          :options="filters.keywords"
          @reset="resetKeywordGroup"
        />
        <MetadataChecklistGroup
          v-model="selectedTagIds"
          v-model:match-mode="tagMatch"
          label="Tags"
          :options="filters.tags"
          @reset="resetTagGroup"
        />
        <MetadataChecklistGroup
          v-model="selectedTypeIds"
          v-model:match-mode="typeMatch"
          label="Types"
          :options="filters.types"
          @reset="resetTypeGroup"
        />
      </div>

      <div class="flex flex-wrap gap-2 border-t border-slate-200 pt-4">
        <GalleryOptionsMenu
          :tooltip-enabled="tooltipEnabled"
          :card-scale="cardScale"
          @update:tooltip-enabled="tooltipEnabled = $event"
          @update:card-scale="cardScale = $event"
        />
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
    </aside>

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
import MetadataChecklistGroup from '@/components/filters/MetadataChecklistGroup.vue';
import SymbolToggleGroup from '@/components/filters/SymbolToggleGroup.vue';
import CardGalleryItem, { type CardGalleryItemModel } from '@/components/cards/CardGalleryItem.vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import type {
  CardFiltersResponse,
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
const { tooltipEnabled, cardScale } = useGalleryOptions();
const manaTypeOptions = computed(() => filterCatalog.value.manaSymbols);
const affinityTypeOptions = computed(() => filterCatalog.value.affinitySymbols);
const devotionTypeOptions = computed(() => filterCatalog.value.devotionSymbols);
const otherSymbolOptions = computed(() => filterCatalog.value.otherSymbols);
const cardHeightRem = computed(() => Number((27 * cardScale.value).toFixed(2)));
const galleryGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(290 * cardScale.value)}px, 1fr))`,
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

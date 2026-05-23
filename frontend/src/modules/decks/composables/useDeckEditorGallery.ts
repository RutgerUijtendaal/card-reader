import { useDebounceFn, useIntersectionObserver } from '@vueuse/core';
import { computed, ref, watch, type Ref } from 'vue';
import { api } from '@/api/client';
import type { CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';
import type { CardFilterSelectionState } from '@/modules/card-filters/cardFilterState';
import { appendGalleryPage, createEmptyGalleryPageState, replaceGalleryPage } from '@/modules/card-search/galleryState';
import type { BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';

type UseDeckEditorGalleryOptions = {
  filtersLoaded: Ref<boolean>;
  buildSearchParams: () => URLSearchParams;
  selectionState: Readonly<Ref<CardFilterSelectionState>>;
  builderStep: Ref<BuilderStep>;
  cardScale: Ref<number>;
  rememberCards: (cards: CardListItem[]) => void;
};

export const useDeckEditorGallery = ({
  filtersLoaded,
  buildSearchParams,
  selectionState,
  builderStep,
  cardScale,
  rememberCards,
}: UseDeckEditorGalleryOptions) => {
  const galleryState = ref(createEmptyGalleryPageState<CardListItem>());
  const isLoadingInitial = ref(false);
  const isLoadingPage = ref(false);
  const loadMoreSentinelRef = ref<HTMLElement | null>(null);
  let latestSearchRequestId = 0;

  const totalCount = computed(() => galleryState.value.count);
  const galleryCards = computed(() => galleryState.value.cards);
  const nextPage = computed(() => galleryState.value.nextPage);
  const isSetupStep = computed(() => builderStep.value === 'setup');
  const cardHeightRem = computed(() => Number(((isSetupStep.value ? 24 : 21) * cardScale.value).toFixed(2)));
  const cardFrameWidthRem = computed(() => Number(((cardHeightRem.value * 63) / 88).toFixed(2)));
  const galleryTileWidthRem = computed(() => Number((cardFrameWidthRem.value + 1.5).toFixed(2)));
  const galleryGridStyle = computed(() => ({
    gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(galleryTileWidthRem.value * 16)}px, 1fr))`,
    justifyContent: 'start',
  }));

  const loadCardsPage = async (page: number, mode: 'replace' | 'append'): Promise<void> => {
    const requestId = ++latestSearchRequestId;
    const params = buildSearchParams();
    params.set('is_hero', isSetupStep.value ? 'true' : 'false');
    params.set('page', String(page));
    params.set('page_size', isSetupStep.value ? '24' : '30');

    if (mode === 'replace') {
      isLoadingInitial.value = true;
    } else {
      isLoadingPage.value = true;
    }

    try {
      const response = await api.get<PaginatedCardsResponse<CardListItem>>(`/cards?${params.toString()}`);
      if (requestId !== latestSearchRequestId) {
        return;
      }
      rememberCards(response.data.results);
      galleryState.value =
        mode === 'replace'
          ? replaceGalleryPage(response.data)
          : appendGalleryPage(galleryState.value, response.data);
    } finally {
      if (requestId === latestSearchRequestId) {
        isLoadingInitial.value = false;
        isLoadingPage.value = false;
      }
    }
  };

  const searchCards = async (): Promise<void> => {
    galleryState.value = createEmptyGalleryPageState<CardListItem>();
    await loadCardsPage(1, 'replace');
  };

  const loadNextPage = async (): Promise<void> => {
    if (isLoadingInitial.value || isLoadingPage.value || nextPage.value === null) {
      return;
    }
    await loadCardsPage(nextPage.value, 'append');
  };

  const setLoadMoreSentinel = (element: HTMLElement | null): void => {
    loadMoreSentinelRef.value = element;
  };

  const debouncedSearchCards = useDebounceFn(() => {
    if (!filtersLoaded.value) {
      return;
    }
    void searchCards();
  }, 200);

  watch(
    selectionState,
    () => {
      debouncedSearchCards();
    },
    { deep: true },
  );

  watch(
    isSetupStep,
    () => {
      if (!filtersLoaded.value) {
        return;
      }
      void searchCards();
    },
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

  return {
    totalCount,
    galleryCards,
    nextPage,
    isLoadingInitial,
    isLoadingPage,
    cardHeightRem,
    galleryTileWidthRem,
    galleryGridStyle,
    searchCards,
    setLoadMoreSentinel,
  };
};

export type DeckEditorGalleryController = ReturnType<typeof useDeckEditorGallery>;

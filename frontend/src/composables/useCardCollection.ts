import { useDebounceFn, useIntersectionObserver } from '@vueuse/core';
import { computed, shallowRef, ref, watch } from 'vue';
import type { Ref, WatchSource } from 'vue';
import { api } from '@/api/client';
import type { PaginatedCardsResponse } from '@/modules/card-detail/types';
import { appendGalleryPage, createEmptyGalleryPageState, replaceGalleryPage } from '@/composables/card-gallery/galleryState';

type IdentifiableCard = {
  id: string;
};

type UseCardCollectionOptions<TCard extends IdentifiableCard> = {
  buildSearchParams: () => URLSearchParams;
  filtersLoaded: Ref<boolean>;
  enabled?: Ref<boolean>;
  resultSetKey?: WatchSource<unknown>;
  pageSize: number | Ref<number>;
  debounceMs?: number;
  watchSource?: WatchSource<unknown> | WatchSource<unknown>[];
  onResults?: (results: TCard[]) => void;
  identity?: (card: TCard) => string;
};

const readPageSize = (value: number | Ref<number>): number =>
  typeof value === 'number' ? value : value.value;

export const useCardCollection = <TCard extends IdentifiableCard>({
  buildSearchParams,
  filtersLoaded,
  enabled,
  resultSetKey,
  pageSize,
  debounceMs = 200,
  watchSource,
  onResults,
  identity,
}: UseCardCollectionOptions<TCard>) => {
  const galleryState = shallowRef(createEmptyGalleryPageState<TCard>());
  const isLoadingInitial = ref(false);
  const isRefreshing = ref(false);
  const isLoadingPage = ref(false);
  const hasLoadedOnce = ref(false);
  const loadMoreSentinelRef = ref<HTMLElement | null>(null);
  let latestSearchRequestId = 0;

  const cards = computed(() => galleryState.value.cards);
  const totalCount = computed(() => galleryState.value.count);
  const nextPage = computed(() => galleryState.value.nextPage);

  const invalidatePendingLoads = (): void => {
    latestSearchRequestId += 1;
    isLoadingInitial.value = false;
    isRefreshing.value = false;
    isLoadingPage.value = false;
  };

  const resetCollection = (): void => {
    invalidatePendingLoads();
    galleryState.value = createEmptyGalleryPageState<TCard>();
    hasLoadedOnce.value = false;
  };

  const loadCardsPage = async (page: number, mode: 'replace' | 'append'): Promise<void> => {
    if (enabled && !enabled.value) {
      return;
    }
    const requestId = ++latestSearchRequestId;
    const params = buildSearchParams();
    params.set('page', String(page));
    params.set('page_size', String(readPageSize(pageSize)));

    if (mode === 'replace' && !hasLoadedOnce.value) {
      isLoadingInitial.value = true;
    } else if (mode === 'replace') {
      isRefreshing.value = true;
    } else {
      isLoadingPage.value = true;
    }

    try {
      const response = await api.get<PaginatedCardsResponse<TCard>>(`/cards?${params.toString()}`);
      if (requestId !== latestSearchRequestId) {
        return;
      }
      onResults?.(response.data.results);
      galleryState.value =
        mode === 'replace'
          ? replaceGalleryPage(response.data)
          : appendGalleryPage(galleryState.value, response.data, identity);
      hasLoadedOnce.value = true;
    } finally {
      if (requestId === latestSearchRequestId) {
        isLoadingInitial.value = false;
        isRefreshing.value = false;
        isLoadingPage.value = false;
      }
    }
  };

  const searchCards = async (): Promise<void> => {
    await loadCardsPage(1, 'replace');
  };

  const loadNextPage = async (): Promise<void> => {
    if ((enabled && !enabled.value) || isLoadingInitial.value || isRefreshing.value || isLoadingPage.value || nextPage.value === null) {
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
  }, debounceMs);

  if (resultSetKey) {
    watch(resultSetKey, resetCollection, { flush: 'sync' });
  }

  if (enabled) {
    watch(
      enabled,
      (isEnabled) => {
        if (!isEnabled) {
          invalidatePendingLoads();
        }
      },
      { flush: 'sync' },
    );
  }

  const collectionWatchSource = [
    ...(Array.isArray(watchSource) ? watchSource : watchSource ? [watchSource] : []),
    ...(resultSetKey ? [resultSetKey] : []),
    ...(enabled ? [enabled] : []),
  ];

  if (collectionWatchSource.length > 0) {
    watch(
      collectionWatchSource,
      () => {
        if (enabled && !enabled.value) {
          return;
        }
        debouncedSearchCards();
      },
      { deep: true },
    );
  }

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
    galleryState,
    cards,
    totalCount,
    nextPage,
    isLoadingInitial,
    isRefreshing,
    isLoadingPage,
    hasLoadedOnce,
    searchCards,
    loadNextPage,
    setLoadMoreSentinel,
  };
};

import { computed, ref } from 'vue';
import type {
  LocationQuery,
  LocationQueryRaw,
  RouteLocationNormalizedLoaded,
  RouteLocationRaw,
  Router,
} from 'vue-router';
import { api } from '@/api/client';
import {
  buildCardFilterRouteQuery,
  parseCardFilterRouteQuery,
} from '@/modules/card-filters/cardFilterState';
import type { GalleryPageState } from '@/modules/card-search/galleryState';
import type { PaginatedCardsResponse } from '@/modules/card-detail/types';

type GalleryNavigationCard = {
  id: string;
};

type GallerySnapshot<TCard extends GalleryNavigationCard> = {
  searchParams: string;
  pageState: GalleryPageState<TCard>;
  scrollTop: number;
};

const galleryCardIds = ref<string[]>([]);
const galleryTotalCount = ref(0);
const galleryNextPage = ref<number | null>(null);
const galleryPageSize = ref(72);
const gallerySearchParams = ref('');
const isLoadingMoreCards = ref(false);
let pendingLoadMorePromise: Promise<void> | null = null;
let gallerySnapshot: GallerySnapshot<GalleryNavigationCard> | null = null;

const normalizeGalleryQuery = (query: LocationQuery): LocationQueryRaw =>
  buildCardFilterRouteQuery(parseCardFilterRouteQuery(query));

export const getGalleryRouteQuery = (query: LocationQuery): LocationQueryRaw => normalizeGalleryQuery(query);

const hasQueryEntries = (query: LocationQueryRaw): boolean => Object.keys(query).length > 0;

export const buildGalleryLocation = (query: LocationQuery): RouteLocationRaw => {
  const galleryQuery = getGalleryRouteQuery(query);
  if (!hasQueryEntries(galleryQuery)) {
    return '/cards';
  }
  return { path: '/cards', query: galleryQuery };
};

export const buildCardDetailLocation = (
  cardId: string,
  query: LocationQuery,
  mode: 'detail' | 'edit',
): RouteLocationRaw => ({
  path: mode === 'edit' ? `/cards/${cardId}/edit` : `/cards/${cardId}`,
  query: getGalleryRouteQuery(query),
});

export const saveGallerySnapshot = <TCard extends GalleryNavigationCard>(
  searchParams: string,
  pageState: GalleryPageState<TCard>,
  scrollTop: number,
): void => {
  gallerySnapshot = {
    searchParams,
    pageState: {
      cards: [...pageState.cards],
      count: pageState.count,
      nextPage: pageState.nextPage,
      page: pageState.page,
      pageSize: pageState.pageSize,
    },
    scrollTop,
  };
};

export const getGallerySnapshot = <TCard extends GalleryNavigationCard>(
  searchParams: string,
): GallerySnapshot<TCard> | null => {
  if (!gallerySnapshot || gallerySnapshot.searchParams !== searchParams) {
    return null;
  }

  return {
    searchParams: gallerySnapshot.searchParams,
    pageState: {
      cards: [...gallerySnapshot.pageState.cards] as TCard[],
      count: gallerySnapshot.pageState.count,
      nextPage: gallerySnapshot.pageState.nextPage,
      page: gallerySnapshot.pageState.page,
      pageSize: gallerySnapshot.pageState.pageSize,
    },
    scrollTop: gallerySnapshot.scrollTop,
  };
};

export const setGalleryNavigationCards = (
  cardIds: string[],
  totalCount: number,
  nextPage: number | null,
  pageSize: number,
  searchParams: string,
): void => {
  galleryCardIds.value = cardIds;
  galleryTotalCount.value = totalCount;
  galleryNextPage.value = nextPage;
  galleryPageSize.value = pageSize;
  gallerySearchParams.value = searchParams;
};

const buildPagedGallerySearch = (): string => {
  const params = new URLSearchParams(gallerySearchParams.value);
  const nextPage = galleryNextPage.value;
  if (nextPage === null) {
    return '';
  }

  params.set('page', String(nextPage));
  params.set('page_size', String(galleryPageSize.value));
  return params.toString();
};

const loadMoreGalleryCards = async (): Promise<void> => {
  if (pendingLoadMorePromise) {
    return pendingLoadMorePromise;
  }

  const queryString = buildPagedGallerySearch();
  if (!queryString) {
    return;
  }

  pendingLoadMorePromise = (async () => {
    isLoadingMoreCards.value = true;
    try {
      const response = await api.get<PaginatedCardsResponse<GalleryNavigationCard>>(`/cards?${queryString}`);
      const seen = new Set(galleryCardIds.value);
      const appendedIds = response.data.results
        .map((card) => card.id)
        .filter((cardId) => !seen.has(cardId));
      galleryCardIds.value = [...galleryCardIds.value, ...appendedIds];
      galleryTotalCount.value = response.data.count;
      galleryNextPage.value = response.data.next_page;
      galleryPageSize.value = response.data.page_size;
    } finally {
      isLoadingMoreCards.value = false;
      pendingLoadMorePromise = null;
    }
  })();

  return pendingLoadMorePromise;
};

export const useGalleryCardNavigation = (
  route: RouteLocationNormalizedLoaded,
  router: Router,
  mode: 'detail' | 'edit',
) => {
  const currentCardId = computed(() => String(route.params.id ?? ''));
  const currentIndex = computed(() => galleryCardIds.value.findIndex((cardId) => cardId === currentCardId.value));
  const hasGalleryContext = computed(() => currentIndex.value >= 0);
  const previousCardId = computed(() =>
    currentIndex.value > 0 ? galleryCardIds.value[currentIndex.value - 1] : null,
  );
  const nextCardId = computed(() =>
    currentIndex.value >= 0 && currentIndex.value < galleryCardIds.value.length - 1
      ? galleryCardIds.value[currentIndex.value + 1]
      : null,
  );
  const hasMoreResults = computed(() => galleryNextPage.value !== null);
  const positionLabel = computed(() => {
    if (!hasGalleryContext.value) return '';
    return `${currentIndex.value + 1} of ${galleryTotalCount.value || galleryCardIds.value.length}`;
  });

  const navigateToCard = (cardId: string | null): void => {
    if (!cardId) return;
    void router.push(buildCardDetailLocation(cardId, route.query, mode));
  };

  const goToPreviousCard = (): void => {
    navigateToCard(previousCardId.value);
  };

  const goToNextCard = async (): Promise<void> => {
    if (nextCardId.value) {
      navigateToCard(nextCardId.value);
      return;
    }

    const isAtLoadedEnd =
      currentIndex.value >= 0 && currentIndex.value === galleryCardIds.value.length - 1;
    if (!isAtLoadedEnd || !hasMoreResults.value) {
      return;
    }

    await loadMoreGalleryCards();
    navigateToCard(nextCardId.value);
  };

  return {
    hasGalleryContext,
    previousCardId,
    nextCardId,
    hasMoreResults,
    isLoadingMoreCards,
    positionLabel,
    goToPreviousCard,
    goToNextCard,
  };
};

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
import { DEFAULT_CARD_PAGE_SIZE } from '@/modules/card-search/pageSize';
import type { GalleryItem, PaginatedCardsResponse } from '@/modules/card-detail/types';

type GalleryNavigationCard = {
  id: string;
  result_type: 'card' | 'card_group';
};

type GallerySnapshot<TCard extends GalleryNavigationCard> = {
  searchParams: string;
  pageState: GalleryPageState<TCard>;
  scrollTop: number;
};

const galleryCards = ref<GalleryNavigationCard[]>([]);
const galleryTotalCount = ref(0);
const galleryNextPage = ref<number | null>(null);
const galleryPageSize = ref(DEFAULT_CARD_PAGE_SIZE);
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

export const buildGalleryItemLocation = (
  item: Pick<GalleryItem, 'id' | 'result_type'>,
  query: LocationQuery,
  mode: 'detail' | 'edit',
): RouteLocationRaw => {
  if (item.result_type === 'card_group') {
    return {
      path: `/card-groups/${item.id}`,
      query: getGalleryRouteQuery(query),
    };
  }
  return buildCardDetailLocation(item.id, query, mode);
};

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
  cards: GalleryNavigationCard[],
  totalCount: number,
  nextPage: number | null,
  pageSize: number,
  searchParams: string,
): void => {
  galleryCards.value = cards;
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
      const seen = new Set(galleryCards.value.map((card) => `${card.result_type}:${card.id}`));
      const appendedCards = response.data.results.filter((card) => !seen.has(`${card.result_type}:${card.id}`));
      galleryCards.value = [...galleryCards.value, ...appendedCards];
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
  const currentResultType = computed<'card' | 'card_group'>(() =>
    route.path.startsWith('/card-groups/') ? 'card_group' : 'card',
  );
  const navigationCards = computed(() =>
    mode === 'edit' ? galleryCards.value.filter((card) => card.result_type === 'card') : galleryCards.value,
  );
  const currentIndex = computed(() =>
    navigationCards.value.findIndex(
      (card) => card.id === currentCardId.value && card.result_type === currentResultType.value,
    ),
  );
  const hasGalleryContext = computed(() => currentIndex.value >= 0);
  const previousCard = computed(() =>
    currentIndex.value > 0 ? navigationCards.value[currentIndex.value - 1] : null,
  );
  const nextCard = computed(() =>
    currentIndex.value >= 0 && currentIndex.value < navigationCards.value.length - 1
      ? navigationCards.value[currentIndex.value + 1]
      : null,
  );
  const hasMoreResults = computed(() => galleryNextPage.value !== null);
  const positionLabel = computed(() => {
    if (!hasGalleryContext.value) return '';
    return `${currentIndex.value + 1} of ${galleryTotalCount.value || navigationCards.value.length}`;
  });

  const navigateToCard = (card: GalleryNavigationCard | null): void => {
    if (!card) return;
    void router.push(buildGalleryItemLocation(card, route.query, mode));
  };

  const goToPreviousCard = (): void => {
    navigateToCard(previousCard.value);
  };

  const goToNextCard = async (): Promise<void> => {
    if (nextCard.value) {
      navigateToCard(nextCard.value);
      return;
    }

    const isAtLoadedEnd =
      currentIndex.value >= 0 && currentIndex.value === navigationCards.value.length - 1;
    if (!isAtLoadedEnd || !hasMoreResults.value) {
      return;
    }

    await loadMoreGalleryCards();
    navigateToCard(nextCard.value);
  };

  return {
    hasGalleryContext,
    previousCardId: computed(() => previousCard.value?.id ?? null),
    nextCardId: computed(() => nextCard.value?.id ?? null),
    hasMoreResults,
    isLoadingMoreCards,
    positionLabel,
    goToPreviousCard,
    goToNextCard,
  };
};

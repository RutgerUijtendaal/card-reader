import { computed, ref } from 'vue';
import type {
  LocationQuery,
  LocationQueryRaw,
  RouteLocationNormalizedLoaded,
  RouteLocationRaw,
  Router,
} from 'vue-router';
import { fetchCards } from '@/domain/cards/api';
import {
  buildCardFilterRouteQuery,
  parseCardFilterRouteQuery,
} from '@/domain/cards/utils/filters/cardFilterRouteState';
import type { GalleryPageState } from '@/domain/cards/utils/gallery/galleryState';
import { DEFAULT_CARD_PAGE_SIZE } from '@/domain/cards/utils/gallery/pageSize';
import type { GalleryItem } from '@/domain/cards/types';
import { isCardPool, type CardPool } from '@/domain/cards/cardPools';

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
let galleryNavigationGeneration = 0;

const invalidatePendingGalleryLoad = (): void => {
  galleryNavigationGeneration += 1;
  pendingLoadMorePromise = null;
  isLoadingMoreCards.value = false;
};

export const clearGalleryNavigationState = (): void => {
  invalidatePendingGalleryLoad();
  galleryCards.value = [];
  galleryTotalCount.value = 0;
  galleryNextPage.value = null;
  gallerySearchParams.value = '';
  gallerySnapshot = null;
};

const normalizeGalleryQuery = (query: LocationQuery): LocationQueryRaw =>
  buildCardFilterRouteQuery(parseCardFilterRouteQuery(query));

export const getGalleryRouteQuery = (query: LocationQuery): LocationQueryRaw => normalizeGalleryQuery(query);

const hasQueryEntries = (query: LocationQueryRaw): boolean => Object.keys(query).length > 0;

const resolveOriginatingCardPool = (query: LocationQuery): CardPool =>
  isCardPool(query.return_card_pool)
    ? query.return_card_pool
    : parseCardFilterRouteQuery(query).cardPool;

export const buildGalleryLocation = (query: LocationQuery): RouteLocationRaw => {
  const galleryQuery = getGalleryRouteQuery(query);
  const returnCardPool = isCardPool(query.return_card_pool)
    ? query.return_card_pool
    : undefined;
  if (returnCardPool === 'player') {
    delete galleryQuery.card_pool;
  } else if (returnCardPool) {
    galleryQuery.card_pool = returnCardPool;
  }
  if (!hasQueryEntries(galleryQuery)) {
    return '/cards';
  }
  return { path: '/cards', query: galleryQuery };
};

export const buildCardDetailLocation = (
  cardId: string,
  query: LocationQuery,
  mode: 'detail' | 'edit',
  cardPool?: CardPool,
): RouteLocationRaw => {
  const cardQuery = getGalleryRouteQuery(query);
  const sourceCardPool = resolveOriginatingCardPool(query);
  if (cardPool && cardPool !== sourceCardPool) {
    cardQuery.return_card_pool = sourceCardPool;
  }
  if (cardPool && cardPool !== 'player') {
    cardQuery.card_pool = cardPool;
  } else if (cardPool === 'player') {
    delete cardQuery.card_pool;
  }
  return {
    path: mode === 'edit' ? `/cards/${cardId}/edit` : `/cards/${cardId}`,
    query: cardQuery,
  };
};

export const buildCardGroupDetailLocation = (
  groupId: string,
  query: LocationQuery,
  cardPool?: CardPool,
): RouteLocationRaw => {
  const groupQuery = getGalleryRouteQuery(query);
  const sourceCardPool = resolveOriginatingCardPool(query);
  if (cardPool && cardPool !== sourceCardPool) {
    groupQuery.return_card_pool = sourceCardPool;
  }
  if (cardPool && cardPool !== 'player') {
    groupQuery.card_pool = cardPool;
  } else if (cardPool === 'player') {
    delete groupQuery.card_pool;
  }
  return {
    path: `/card-groups/${groupId}`,
    query: groupQuery,
  };
};

export const buildGalleryItemLocation = (
  item: Pick<GalleryItem, 'id' | 'result_type'>,
  query: LocationQuery,
  mode: 'detail' | 'edit',
): RouteLocationRaw => {
  if (item.result_type === 'card_group') {
    return buildCardGroupDetailLocation(item.id, query);
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
  invalidatePendingGalleryLoad();
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

  const requestGeneration = galleryNavigationGeneration;
  const requestPromise = (async () => {
    isLoadingMoreCards.value = true;
    try {
      const response = await fetchCards<GalleryNavigationCard>(new URLSearchParams(queryString));
      if (requestGeneration !== galleryNavigationGeneration) {
        return;
      }
      const seen = new Set(galleryCards.value.map((card) => `${card.result_type}:${card.id}`));
      const appendedCards = response.results.filter((card) => !seen.has(`${card.result_type}:${card.id}`));
      galleryCards.value = [...galleryCards.value, ...appendedCards];
      galleryTotalCount.value = response.count;
      galleryNextPage.value = response.next_page;
      galleryPageSize.value = response.page_size;
    } catch (error) {
      if (requestGeneration === galleryNavigationGeneration) {
        throw error;
      }
    } finally {
      if (requestGeneration === galleryNavigationGeneration) {
        isLoadingMoreCards.value = false;
        pendingLoadMorePromise = null;
      }
    }
  })();
  pendingLoadMorePromise = requestPromise;

  return requestPromise;
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

    const navigationGeneration = galleryNavigationGeneration;
    await loadMoreGalleryCards();
    if (navigationGeneration !== galleryNavigationGeneration) {
      return;
    }
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

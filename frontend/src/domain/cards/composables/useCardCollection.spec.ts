import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { api } from '@/shared/api/client';
import { useCardCollection } from '@/domain/cards/composables/useCardCollection';

vi.mock('@/shared/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

type TestCard = {
  id: string;
  name: string;
};

const mockedGet = vi.mocked(api.get);

const buildResponse = (results: TestCard[], nextPage: number | null = null) => ({
  data: {
    results,
    count: results.length,
    next_page: nextPage,
    previous_page: null,
    page: nextPage === null ? 1 : nextPage - 1,
    page_size: 30,
  },
});

const createDeferred = <T,>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
};

describe('useCardCollection', () => {
  beforeEach(() => {
    mockedGet.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  test('marks the first search as an initial load and tracks completion', async () => {
    const deferred = createDeferred<ReturnType<typeof buildResponse>>();
    mockedGet.mockReturnValueOnce(deferred.promise);

    const collection = useCardCollection<TestCard>({
      buildSearchParams: () => new URLSearchParams(),
      filtersLoaded: ref(true),
      pageSize: 30,
    });

    const pendingSearch = collection.searchCards();

    expect(collection.isLoadingInitial.value).toBe(true);
    expect(collection.isRefreshing.value).toBe(false);
    expect(collection.hasLoadedOnce.value).toBe(false);
    expect(collection.cards.value).toEqual([]);

    deferred.resolve(buildResponse([{ id: 'card-1', name: 'First Card' }]));
    await pendingSearch;

    expect(collection.isLoadingInitial.value).toBe(false);
    expect(collection.isRefreshing.value).toBe(false);
    expect(collection.hasLoadedOnce.value).toBe(true);
    expect(collection.cards.value).toEqual([{ id: 'card-1', name: 'First Card' }]);
  });

  test('preserves existing cards during refresh loads', async () => {
    mockedGet.mockResolvedValueOnce(buildResponse([{ id: 'card-1', name: 'First Card' }]));

    const collection = useCardCollection<TestCard>({
      buildSearchParams: () => new URLSearchParams(),
      filtersLoaded: ref(true),
      pageSize: 30,
    });

    await collection.searchCards();

    const deferred = createDeferred<ReturnType<typeof buildResponse>>();
    mockedGet.mockReturnValueOnce(deferred.promise);

    const refreshSearch = collection.searchCards();

    expect(collection.isLoadingInitial.value).toBe(false);
    expect(collection.isRefreshing.value).toBe(true);
    expect(collection.cards.value).toEqual([{ id: 'card-1', name: 'First Card' }]);

    deferred.resolve(buildResponse([{ id: 'card-2', name: 'Second Card' }]));
    await refreshSearch;

    expect(collection.isRefreshing.value).toBe(false);
    expect(collection.cards.value).toEqual([{ id: 'card-2', name: 'Second Card' }]);
  });

  test('uses page loading only for pagination requests', async () => {
    mockedGet.mockResolvedValueOnce(buildResponse([{ id: 'card-1', name: 'First Card' }], 2));

    const collection = useCardCollection<TestCard>({
      buildSearchParams: () => new URLSearchParams(),
      filtersLoaded: ref(true),
      pageSize: 30,
    });

    await collection.searchCards();

    const deferred = createDeferred<ReturnType<typeof buildResponse>>();
    mockedGet.mockReturnValueOnce(deferred.promise);

    const pendingLoad = collection.loadNextPage();

    expect(collection.isLoadingPage.value).toBe(true);
    expect(collection.isRefreshing.value).toBe(false);
    expect(collection.isLoadingInitial.value).toBe(false);

    deferred.resolve(
      buildResponse(
        [
          { id: 'card-1', name: 'First Card' },
          { id: 'card-2', name: 'Second Card' },
        ],
        null,
      ),
    );
    await pendingLoad;

    expect(collection.isLoadingPage.value).toBe(false);
    expect(collection.cards.value).toEqual([
      { id: 'card-1', name: 'First Card' },
      { id: 'card-2', name: 'Second Card' },
    ]);
  });

  test('does not let stale refresh responses clear active loading state', async () => {
    mockedGet.mockResolvedValueOnce(buildResponse([{ id: 'card-1', name: 'First Card' }]));

    const collection = useCardCollection<TestCard>({
      buildSearchParams: () => new URLSearchParams(),
      filtersLoaded: ref(true),
      pageSize: 30,
    });

    await collection.searchCards();

    const staleDeferred = createDeferred<ReturnType<typeof buildResponse>>();
    const latestDeferred = createDeferred<ReturnType<typeof buildResponse>>();
    mockedGet.mockReturnValueOnce(staleDeferred.promise).mockReturnValueOnce(latestDeferred.promise);

    const staleSearch = collection.searchCards();
    const latestSearch = collection.searchCards();

    expect(collection.isRefreshing.value).toBe(true);

    staleDeferred.resolve(buildResponse([{ id: 'card-stale', name: 'Stale Card' }]));
    await staleSearch;

    expect(collection.isRefreshing.value).toBe(true);
    expect(collection.cards.value).toEqual([{ id: 'card-1', name: 'First Card' }]);

    latestDeferred.resolve(buildResponse([{ id: 'card-2', name: 'Second Card' }]));
    await latestSearch;

    expect(collection.isRefreshing.value).toBe(false);
    expect(collection.cards.value).toEqual([{ id: 'card-2', name: 'Second Card' }]);
  });

  test('does not start pagination while a replace refresh is in flight', async () => {
    mockedGet.mockResolvedValueOnce(
      buildResponse([{ id: 'card-1', name: 'First Card' }], 2),
    );

    const collection = useCardCollection<TestCard>({
      buildSearchParams: () => new URLSearchParams(),
      filtersLoaded: ref(true),
      pageSize: 30,
    });

    await collection.searchCards();

    const refreshDeferred = createDeferred<ReturnType<typeof buildResponse>>();
    mockedGet.mockReturnValueOnce(refreshDeferred.promise);

    const refreshSearch = collection.searchCards();

    expect(collection.isRefreshing.value).toBe(true);

    await collection.loadNextPage();

    expect(mockedGet).toHaveBeenCalledTimes(2);
    expect(collection.isLoadingPage.value).toBe(false);
    expect(collection.cards.value).toEqual([{ id: 'card-1', name: 'First Card' }]);

    refreshDeferred.resolve(buildResponse([{ id: 'card-2', name: 'Refreshed Card' }], null));
    await refreshSearch;

    expect(collection.isRefreshing.value).toBe(false);
    expect(collection.cards.value).toEqual([{ id: 'card-2', name: 'Refreshed Card' }]);
  });

  test('does not search or paginate while the collection is disabled', async () => {
    const collection = useCardCollection<TestCard>({
      buildSearchParams: () => new URLSearchParams(),
      filtersLoaded: ref(true),
      enabled: ref(false),
      pageSize: 30,
    });

    await collection.searchCards();
    await collection.loadNextPage();

    expect(mockedGet).not.toHaveBeenCalled();
    expect(collection.hasLoadedOnce.value).toBe(false);
  });

  test('loads the collection when it becomes enabled', async () => {
    vi.useFakeTimers();
    mockedGet.mockResolvedValueOnce(buildResponse([{ id: 'card-1', name: 'First Card' }]));
    const enabled = ref(false);
    const collection = useCardCollection<TestCard>({
      buildSearchParams: () => new URLSearchParams(),
      filtersLoaded: ref(true),
      enabled,
      pageSize: 30,
      debounceMs: 0,
    });

    enabled.value = true;
    await nextTick();
    await vi.runAllTimersAsync();

    expect(mockedGet).toHaveBeenCalledTimes(1);
    expect(collection.cards.value).toEqual([{ id: 'card-1', name: 'First Card' }]);
  });

  test('clears results and ignores pending responses when the result set changes', async () => {
    vi.useFakeTimers();
    mockedGet.mockResolvedValueOnce(buildResponse([{ id: 'hero-1', name: 'Hero' }]));
    const pendingHeroRefresh = createDeferred<ReturnType<typeof buildResponse>>();
    mockedGet.mockReturnValueOnce(pendingHeroRefresh.promise);
    mockedGet.mockResolvedValueOnce(buildResponse([{ id: 'card-1', name: 'Card' }]));
    const resultSetKey = ref('heroes');
    const collection = useCardCollection<TestCard>({
      buildSearchParams: () => new URLSearchParams(),
      filtersLoaded: ref(true),
      resultSetKey,
      pageSize: 30,
      debounceMs: 0,
    });

    await collection.searchCards();
    const pendingRefresh = collection.searchCards();
    expect(collection.cards.value).toEqual([{ id: 'hero-1', name: 'Hero' }]);

    resultSetKey.value = 'cards';
    expect(collection.cards.value).toEqual([]);
    expect(collection.hasLoadedOnce.value).toBe(false);

    pendingHeroRefresh.resolve(buildResponse([{ id: 'hero-stale', name: 'Stale Hero' }]));
    await pendingRefresh;
    expect(collection.cards.value).not.toContainEqual({ id: 'hero-stale', name: 'Stale Hero' });

    await nextTick();
    await vi.runAllTimersAsync();
    expect(collection.cards.value).toEqual([{ id: 'card-1', name: 'Card' }]);
  });
});

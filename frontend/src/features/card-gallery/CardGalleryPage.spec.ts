import { createApp, h, nextTick } from 'vue';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter, RouterView } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { RouteLocationRaw } from 'vue-router';
import CardGalleryPage from '@/features/card-gallery/CardGalleryPage.vue';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import type { CardFiltersResponse } from '@/domain/cards/types';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('@/shared/api/client', () => ({
  api: {
    get: apiGet,
    post: vi.fn(),
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => ({ canAccessStaffRoutes: false }),
}));

const filters: CardFiltersResponse = {
  keywords: [],
  tags: [
    { id: 'tag-dragon', key: 'dragon', label: 'Dragon' },
    { id: 'tag-old', key: 'old', label: 'Old' },
    { id: 'tag-new', key: 'new', label: 'New' },
  ],
  symbols: [],
  types: [],
  card_pools: [
    { key: 'player', label: 'Player', rank: 0 },
    { key: 'evil', label: 'Evil', rank: 1 },
    { key: 'neutral', label: 'Neutral', rank: 2 },
  ],
  card_roles: [
    { key: 'hero', label: 'Hero', rank: 1 },
    { key: 'boss', label: 'Boss', rank: 2 },
  ],
  card_factions: [
    { key: 'order', label: 'Order', rank: 1 },
    { key: 'blood', label: 'Blood', rank: 2 },
  ],
};

const emptyCardsPage = {
  count: 0,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 30,
  results: [],
};

const flushPromises = async (): Promise<void> => {
  for (let index = 0; index < 8; index += 1) {
    await Promise.resolve();
    await nextTick();
  }
};

const createDeferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
};

const mountGallery = async (
  path: string,
  activePool: 'player' | 'evil' | 'neutral',
  fetchCards = () => Promise.resolve({ data: emptyCardsPage }),
  fetchFilters: (
    pool: 'player' | 'evil' | 'neutral',
  ) => Promise<{ data: CardFiltersResponse }> = () => Promise.resolve({ data: filters }),
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const requestRoutes: string[] = [];
  const filterRequests: string[] = [];
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/cards', component: CardGalleryPage }],
  });

  apiGet.mockImplementation((
    url: string,
    config?: { params?: { card_pool?: 'player' | 'evil' | 'neutral' } },
  ) => {
    if (url === '/cards/filters') {
      const pool = config?.params?.card_pool;
      if (!pool) return Promise.reject(new Error('Gallery filter request omitted its card pool'));
      filterRequests.push(pool);
      return fetchFilters(pool);
    }
    if (url.startsWith('/cards?')) {
      requestRoutes.push(router.currentRoute.value.fullPath);
      return fetchCards();
    }
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });

  await router.push(path);
  await router.isReady();

  const pinia = createPinia();
  const workspace = useCardPoolWorkspaceStore(pinia);
  workspace.synchronizeSession(['player', 'evil', 'neutral'], 'staff-user');
  workspace.selectPool(activePool);

  const app = createApp({ render: () => h(RouterView) });
  app.use(router);
  app.use(pinia);
  app.mount(container);
  await flushPromises();
  await vi.waitFor(() => {
    expect(requestRoutes.length).toBeGreaterThan(0);
  });

  return {
    container,
    filterRequests,
    requestRoutes,
    router,
    workspace,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('CardGalleryPage pool-aware filters', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test.each([
    ['player', '/cards', '.lucide-shield'],
    ['evil', '/cards?card_pool=evil', '.card-pool-icon-evil'],
    ['neutral', '/cards?card_pool=neutral', '.lucide-scale'],
  ] as const)('uses the %s pool icon in the Gallery header', async (activePool, path, iconSelector) => {
    const mounted = await mountGallery(path, activePool);

    expect(mounted.container.querySelector(
      `.app-page-header-primary ${iconSelector}`,
    )).not.toBeNull();

    mounted.unmount();
  });

  test('canonicalizes an Evil direct URL before requesting cards', async () => {
    const mounted = await mountGallery(
      '/cards?card_pool=evil&card_roles=boss&card_role_match=all'
        + '&card_factions=blood&card_faction_match=all&mana_family_keys=dark'
        + '&mana_cost_min=2&affinity_symbol_keys=dark-affinity'
        + '&devotion_symbol_keys=blood-devotion&tag_keys=dragon',
      'evil',
    );

    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/cards?card_pool=evil&card_faction_match=all&card_factions=blood&tag_keys=dragon',
    );
    expect(mounted.requestRoutes).toEqual([mounted.router.currentRoute.value.fullPath]);

    const cardRequest = apiGet.mock.calls.find(([url]) =>
      typeof url === 'string' && url.startsWith('/cards?'),
    )?.[0];
    const params = new URL(String(cardRequest), 'https://cards.test').searchParams;
    expect(params.get('card_pool')).toBe('evil');
    expect(params.getAll('card_factions')).toEqual(['blood']);
    expect(params.get('card_faction_match')).toBe('all');
    expect(params.has('card_roles')).toBe(false);
    expect(params.has('card_role_exclude')).toBe(false);
    expect(params.has('mana_family_keys')).toBe(false);
    expect(params.has('mana_cost_min')).toBe(false);
    expect(params.has('affinity_symbol_ids')).toBe(false);
    expect(params.has('devotion_symbol_ids')).toBe(false);

    const text = mounted.container.textContent ?? '';
    expect(text).toContain('Factions');
    expect(text).not.toContain('Card roles');
    expect(text).not.toContain('Mana');
    expect(text).not.toContain('Affinity');
    expect(text).not.toContain('Devotion');

    mounted.unmount();
  });

  test('removes Evil factions when the same route state enters Neutral', async () => {
    const mounted = await mountGallery(
      '/cards?card_pool=neutral&card_factions=blood&card_faction_match=all&tag_keys=dragon',
      'neutral',
    );

    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/cards?card_pool=neutral&tag_keys=dragon',
    );
    const text = mounted.container.textContent ?? '';
    expect(text).not.toContain('Card roles');
    expect(text).not.toContain('Factions');
    expect(text).not.toContain('Mana');
    expect(text).not.toContain('Affinity');
    expect(text).not.toContain('Devotion');

    mounted.unmount();
  });

  test('invalidates an in-flight request before awaiting canonical route replacement', async () => {
    const staleResponse = createDeferred<{ data: typeof emptyCardsPage }>();
    const releaseCanonicalReplace = createDeferred<void>();
    let requestCount = 0;
    const mounted = await mountGallery('/cards?tag_keys=old', 'player', () => {
      requestCount += 1;
      return requestCount === 1
        ? staleResponse.promise
        : Promise.resolve({ data: emptyCardsPage });
    });
    const originalReplace = mounted.router.replace.bind(mounted.router);
    const replaceSpy = vi.spyOn(mounted.router, 'replace').mockImplementation(
      async (to: RouteLocationRaw) => {
        await releaseCanonicalReplace.promise;
        return originalReplace(to);
      },
    );

    await mounted.router.push('/cards?card_roles=hero&tag_keys=new');
    await vi.waitFor(() => {
      expect(replaceSpy).toHaveBeenCalledTimes(1);
    });

    staleResponse.resolve({ data: { ...emptyCardsPage, count: 37 } });
    await flushPromises();

    expect(mounted.container.textContent).not.toContain('37 results');

    releaseCanonicalReplace.resolve();
    await vi.waitFor(() => {
      expect(mounted.requestRoutes).toHaveLength(2);
    });
    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards?tag_keys=new');

    mounted.unmount();
  });

  test('removes unavailable metadata keys after exact-pool hydration', async () => {
    const evilFilters = {
      ...filters,
      keywords: [{ id: 'keyword-evil', key: 'evil-keyword', label: 'Evil Keyword' }],
      tags: [{ id: 'tag-evil', key: 'evil-tag', label: 'Evil Tag' }],
      types: [{ id: 'type-evil', key: 'evil-type', label: 'Evil Type' }],
    };
    const mounted = await mountGallery(
      '/cards?card_pool=evil&keyword_match=all&keyword_keys=player-keyword'
        + '&tag_match=all&tag_keys=evil-tag&tag_keys=player-tag'
        + '&type_match=all&type_keys=evil-type&type_keys=player-type'
        + '&type_exclude_keys=missing-type',
      'evil',
      undefined,
      () => Promise.resolve({ data: evilFilters }),
    );

    expect(mounted.filterRequests).toEqual(['evil']);
    expect(mounted.router.currentRoute.value.query).toEqual({
      card_pool: 'evil',
      tag_match: 'all',
      tag_keys: ['evil-tag'],
      type_match: 'all',
      type_keys: ['evil-type'],
    });
    const cardRequest = apiGet.mock.calls.find(([url]) =>
      typeof url === 'string' && url.startsWith('/cards?'),
    )?.[0];
    const params = new URL(String(cardRequest), 'https://cards.test').searchParams;
    expect(params.getAll('keyword_ids')).toEqual([]);
    expect(params.getAll('tag_ids')).toEqual(['tag-evil']);
    expect(params.getAll('type_ids')).toEqual(['type-evil']);
    expect(params.getAll('type_exclude_ids')).toEqual([]);

    mounted.unmount();
  });

  test('keeps route metadata intact and browsing usable when facet hydration fails', async () => {
    const mounted = await mountGallery(
      '/cards?tag_keys=keep-on-failure',
      'player',
      undefined,
      () => Promise.reject(new Error('facet failure')),
    );

    expect(mounted.filterRequests).toEqual(['player']);
    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards?tag_keys=keep-on-failure');
    expect(mounted.requestRoutes).toEqual(['/cards?tag_keys=keep-on-failure']);
    expect(mounted.container.textContent).toContain('Filter options could not be loaded');

    mounted.unmount();
  });

  test('does not restore an unfiltered fallback snapshot after facet retry succeeds', async () => {
    let filterRequestCount = 0;
    const mounted = await mountGallery(
      '/cards?tag_keys=recovered-tag',
      'player',
      undefined,
      () => {
        filterRequestCount += 1;
        if (filterRequestCount === 1) {
          return Promise.reject(new Error('facet failure'));
        }
        return Promise.resolve({
          data: {
            ...filters,
            tags: [{ id: 'tag-recovered', key: 'recovered-tag', label: 'Recovered Tag' }],
          },
        });
      },
    );

    const retryButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Retry filter options',
    );
    expect(retryButton).toBeDefined();
    retryButton?.click();

    await vi.waitFor(() => {
      expect(mounted.requestRoutes).toHaveLength(2);
    });
    const cardRequests = apiGet.mock.calls.filter(([url]) =>
      typeof url === 'string' && url.startsWith('/cards?'),
    );
    expect(cardRequests).toHaveLength(2);
    const recoveredParams = new URL(String(cardRequests[1]?.[0]), 'https://cards.test').searchParams;
    expect(recoveredParams.getAll('tag_ids')).toEqual(['tag-recovered']);

    mounted.unmount();
  });

  test('reconciles metadata when switching between pool catalogs', async () => {
    const poolFilters: Record<'player' | 'evil' | 'neutral', CardFiltersResponse> = {
      player: {
        ...filters,
        tags: [{ id: 'tag-player', key: 'player-tag', label: 'Player Tag' }],
      },
      evil: {
        ...filters,
        tags: [{ id: 'tag-evil', key: 'evil-tag', label: 'Evil Tag' }],
      },
      neutral: { ...filters, tags: [] },
    };
    const mounted = await mountGallery(
      '/cards?tag_keys=player-tag',
      'player',
      undefined,
      (pool) => Promise.resolve({ data: poolFilters[pool] }),
    );

    mounted.workspace.selectPool('evil');
    await vi.waitFor(() => {
      expect(mounted.filterRequests).toEqual(['player', 'evil']);
      expect(mounted.router.currentRoute.value.fullPath).toBe('/cards?card_pool=evil');
    });
    expect(mounted.requestRoutes.at(-1)).toBe('/cards?card_pool=evil');

    mounted.unmount();
  });
});

import { createApp, h, nextTick } from 'vue';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter, RouterView } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { RouteLocationRaw } from 'vue-router';
import CardGalleryPage from '@/features/card-gallery/CardGalleryPage.vue';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';

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

const filters = {
  keywords: [],
  tags: [],
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
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const requestRoutes: string[] = [];
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/cards', component: CardGalleryPage }],
  });

  apiGet.mockImplementation((url: string) => {
    if (url === '/cards/filters') {
      return Promise.resolve({ data: filters });
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
    requestRoutes,
    router,
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
});

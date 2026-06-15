/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter, type Router } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import DeckIndexPage from '@/modules/decks/DeckIndexPage.vue';

const {
  authState,
  apiGetMock,
  deleteDeckMock,
  fetchMyDeckSummariesMock,
  fetchPublicDeckSummariesMock,
  updateDeckMock,
} = vi.hoisted(() => ({
  authState: {
    authEnabled: true,
    authenticated: true,
  },
  apiGetMock: vi.fn(),
  deleteDeckMock: vi.fn(),
  fetchMyDeckSummariesMock: vi.fn(),
  fetchPublicDeckSummariesMock: vi.fn(),
  updateDeckMock: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  api: {
    get: apiGetMock,
  },
}));

vi.mock('@/modules/auth/authStore', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/modules/decks/api', () => ({
  deleteDeck: deleteDeckMock,
  fetchMyDeckSummaries: fetchMyDeckSummariesMock,
  fetchPublicDeckSummaries: fetchPublicDeckSummariesMock,
  updateDeck: updateDeckMock,
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock('@/composables/useDeckExport', () => ({
  useDeckExport: () => ({
    exportTtsDeck: vi.fn(),
  }),
}));

vi.mock('@/components/app/AppPageHeader.vue', () => ({
  default: defineComponent({
    props: {
      title: { type: String, required: true },
    },
    setup(props, { slots }) {
      return () =>
        h('header', [
          h('h1', props.title),
          slots.actions?.(),
        ]);
    },
  }),
}));

vi.mock('@/components/app/AppSelect.vue', () => ({
  default: defineComponent({
    props: {
      modelValue: { type: String, default: null },
      options: { type: Array, default: () => [] },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
      return () =>
        h(
          'select',
          {
            value: props.modelValue ?? '',
            onChange: (event: Event) => {
              emit('update:modelValue', (event.target as HTMLSelectElement).value);
            },
          },
          (props.options as Array<{ value: string; label: string }>).map((option) =>
            h('option', { value: option.value }, option.label),
          ),
        );
    },
  }),
}));

vi.mock('@/components/modals/ConfirmModal.vue', () => ({
  default: defineComponent({
    setup() {
      return () => null;
    },
  }),
}));

vi.mock('@/components/app/ExtraActionsMenu.vue', () => ({
  default: defineComponent({
    setup(_, { slots }) {
      return () => h('div', { 'data-testid': 'extra-actions-menu' }, slots.default?.({ close: () => undefined }));
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckBrowseFiltersPanel.vue', () => ({
  default: defineComponent({
    props: {
      canUseOwnedDecks: { type: Boolean, default: false },
      controller: { type: Object, required: true },
      description: { type: String, required: true },
      mode: { type: String, required: true },
      ownedTo: { type: Object, required: true },
      publicTo: { type: Object, required: true },
      totalCount: { type: Number, required: true },
    },
    setup(props) {
      const routeHref = (to: { path?: string; query?: Record<string, unknown> }): string => {
        const params = new URLSearchParams();
        Object.entries(to.query ?? {}).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            params.set(key, String(value));
          }
        });
        const query = params.toString();
        return `${to.path ?? ''}${query ? `?${query}` : ''}`;
      };
      return () =>
        h('aside', [
          h('p', props.description),
          props.canUseOwnedDecks
            ? [
                h('a', { href: routeHref(props.publicTo as { path?: string; query?: Record<string, unknown> }) }, 'Public'),
                h('a', { href: routeHref(props.ownedTo as { path?: string; query?: Record<string, unknown> }) }, 'My Decks'),
              ]
            : null,
          h('span', `Total ${props.totalCount}`),
          h('input', {
            'data-testid': 'deck-query',
            value: (props.controller as { query: { value: string } }).query.value,
            onInput: (event: Event) => {
              (props.controller as { updateQuery: (value: string) => void }).updateQuery(
                (event.target as HTMLInputElement).value,
              );
            },
          }),
        ]);
    },
  }),
}));

vi.mock('@/components/decks/DeckListCard.vue', () => ({
  default: defineComponent({
    props: {
      deck: { type: Object, required: true },
      mode: { type: String, required: true },
      titleTo: { type: String, required: true },
    },
    setup(props, { slots }) {
      return () =>
        h(
          'article',
          {
            'data-mode': props.mode,
            'data-title-to': props.titleTo,
          },
          [
            h('h2', (props.deck as { name: string }).name),
            slots.actions?.(),
          ],
        );
    },
  }),
}));

const deckRecord = {
  id: 'deck-1',
  name: 'Starter Deck',
  description: 'A test deck',
  visibility: 'public' as const,
  owner: {
    id: 'user-1',
    username: 'owner',
  },
  hero_card: {
    id: 'card-1',
    key: 'card-1',
    name: 'Hero',
    image_url: null,
    mana_cost: null,
    mana_value: null,
    mana_symbols: [],
    types: [],
    keywords: [],
    tags: [],
  },
  mainboard: {
    total_cards: 40,
    unique_cards: 20,
    entries: [],
  },
  sideboards: [],
  totals: {
    overall_total_cards: 40,
    overall_unique_cards: 20,
    mainboard_total_cards: 40,
    mainboard_unique_cards: 20,
  },
  status: {
    is_valid: true,
    label: 'Ready',
    issues: [],
  },
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const filtersPayload = {
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

const createDeferred = <T,>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
};

const flushPage = async (): Promise<void> => {
  await nextTick();
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
  await nextTick();
};

const mountPage = async (
  path: string,
): Promise<{
  container: HTMLElement;
  router: Router;
  unmount: () => void;
}> => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/decks', component: DeckIndexPage },
      { path: '/decks/:id', component: { template: '<div />' } },
      { path: '/my/decks', component: DeckIndexPage },
      { path: '/my/decks/:id', component: { template: '<div />' } },
      { path: '/my/decks/:id/edit', component: { template: '<div />' } },
      { path: '/my/decks/new', component: { template: '<div />' } },
    ],
  });
  await router.push(path);
  await router.isReady();

  const app = createApp(DeckIndexPage);
  app.use(router);
  app.mount(container);
  await flushPage();

  return {
    container,
    router,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const lastSearchParams = (mock: ReturnType<typeof vi.fn>): URLSearchParams => {
  const call = mock.mock.calls.at(-1);
  const params = call?.[0];
  if (!(params instanceof URLSearchParams)) {
    throw new Error('expected URLSearchParams');
  }
  return params;
};

describe('DeckIndexPage', () => {
  beforeEach(() => {
    authState.authenticated = true;
    authState.authEnabled = true;
    apiGetMock.mockResolvedValue({ data: filtersPayload });
    fetchMyDeckSummariesMock.mockResolvedValue([deckRecord]);
    fetchPublicDeckSummariesMock.mockResolvedValue([deckRecord]);
    updateDeckMock.mockResolvedValue(deckRecord);
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  test('renders public mode on /decks and calls fetchPublicDecks', async () => {
    const mounted = await mountPage('/decks');

    expect(fetchPublicDeckSummariesMock).toHaveBeenCalledTimes(1);
    expect(fetchMyDeckSummariesMock).not.toHaveBeenCalled();
    expect(mounted.container.querySelector('[data-mode="browse"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-title-to="/decks/deck-1"]')).not.toBeNull();
    expect(mounted.container.textContent).toContain('Search public decks');

    mounted.unmount();
  });

  test('renders deck skeleton cards while deck filters are loading', async () => {
    apiGetMock.mockReturnValue(new Promise(() => undefined));
    const mounted = await mountPage('/decks');

    expect(mounted.container.querySelectorAll('.deck-loading-skeleton')).toHaveLength(10);
    expect(mounted.container.textContent).not.toContain('Loading decks');

    mounted.unmount();
  });

  test('renders owned mode on /my/decks and calls fetchMyDecks', async () => {
    const mounted = await mountPage('/my/decks');

    expect(fetchMyDeckSummariesMock).toHaveBeenCalledTimes(1);
    expect(fetchPublicDeckSummariesMock).not.toHaveBeenCalled();
    expect(mounted.container.querySelector('[data-mode="owned"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-title-to="/my/decks/deck-1"]')).not.toBeNull();
    expect(mounted.container.textContent).toContain('Search your decks');

    mounted.unmount();
  });

  test('ignores stale deck responses after switching between public and owned modes', async () => {
    const publicDeferred = createDeferred<Array<typeof deckRecord>>();
    fetchPublicDeckSummariesMock.mockReturnValueOnce(publicDeferred.promise);
    fetchMyDeckSummariesMock.mockResolvedValueOnce([
      {
        ...deckRecord,
        id: 'owned-deck',
        name: 'Owned Deck',
      },
    ]);
    const mounted = await mountPage('/decks');

    await mounted.router.push('/my/decks');
    await flushPage();

    publicDeferred.resolve([
      {
        ...deckRecord,
        id: 'public-deck',
        name: 'Public Deck',
      },
    ]);
    await flushPage();

    expect(mounted.container.textContent).toContain('Owned Deck');
    expect(mounted.container.textContent).not.toContain('Public Deck');
    expect(mounted.container.querySelector('[data-mode="owned"]')).not.toBeNull();

    mounted.unmount();
  });

  test('tabs link to public and owned deck routes with the shared deck search query', async () => {
    const mounted = await mountPage('/decks?q=Blade');
    const links = Array.from(mounted.container.querySelectorAll<HTMLAnchorElement>('a'));
    const publicLink = links.find((link) => link.textContent?.trim() === 'Public');
    const ownedLink = links.find((link) => link.textContent?.trim() === 'My Decks');

    expect(publicLink).toBeDefined();
    expect(ownedLink).toBeDefined();

    const publicUrl = new URL(publicLink?.getAttribute('href') ?? '', 'http://localhost');
    expect(publicUrl.pathname).toBe('/decks');
    expect(publicUrl.searchParams.get('q')).toBe('Blade');

    const ownedUrl = new URL(ownedLink?.getAttribute('href') ?? '', 'http://localhost');
    expect(ownedUrl.pathname).toBe('/my/decks');
    expect(ownedUrl.searchParams.get('q')).toBe('Blade');

    mounted.unmount();
  });

  test('hides the deck library tab selector for anonymous public browsing', async () => {
    authState.authenticated = false;
    authState.authEnabled = true;
    const mounted = await mountPage('/decks');
    const links = Array.from(mounted.container.querySelectorAll<HTMLAnchorElement>('a'));

    expect(links.find((link) => link.textContent?.trim() === 'Public')).toBeUndefined();
    expect(links.find((link) => link.textContent?.trim() === 'My Decks')).toBeUndefined();
    expect(mounted.container.textContent).toContain('Search public decks');
    expect(fetchPublicDeckSummariesMock).toHaveBeenCalledTimes(1);
    expect(fetchMyDeckSummariesMock).not.toHaveBeenCalled();

    mounted.unmount();
  });

  test('owned actions keep one edit action with extra actions and visibility select', async () => {
    const mounted = await mountPage('/my/decks');
    const text = mounted.container.textContent ?? '';

    expect(text).toContain('Copy Share Link');
    expect(text).toContain('Copy TTS');
    expect(text).toContain('Delete');
    expect(text.match(/\bEdit\b/g) ?? []).toHaveLength(1);
    expect(mounted.container.querySelector('select')).not.toBeNull();

    mounted.unmount();
  });

  test('owned visibility changes send a partial deck patch', async () => {
    const mounted = await mountPage('/my/decks');
    const select = mounted.container.querySelector<HTMLSelectElement>('select');
    if (!select) {
      throw new Error('expected visibility select');
    }

    select.value = 'private';
    select.dispatchEvent(new Event('change'));
    await flushPage();

    expect(updateDeckMock).toHaveBeenCalledWith('deck-1', { visibility: 'private' });

    mounted.unmount();
  });

  test.each([
    ['/decks', fetchPublicDeckSummariesMock],
    ['/my/decks', fetchMyDeckSummariesMock],
  ])('passes route filters to API params for %s', async (path, fetchMock) => {
    const mounted = await mountPage(`${path}?q=Blade`);

    expect(lastSearchParams(fetchMock).get('q')).toBe('Blade');

    mounted.unmount();
  });

  test.each(['/decks', '/my/decks'])('filter input updates the %s route query', async (path) => {
    vi.useFakeTimers();
    const mounted = await mountPage(path);
    const input = mounted.container.querySelector<HTMLInputElement>('[data-testid="deck-query"]');
    if (!input) {
      throw new Error('expected deck filter input');
    }

    input.value = 'Blade';
    input.dispatchEvent(new Event('input'));
    await nextTick();
    await vi.advanceTimersByTimeAsync(300);
    await flushPage();

    expect(mounted.router.currentRoute.value.query.q).toBe('Blade');

    mounted.unmount();
  });
});

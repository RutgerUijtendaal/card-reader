/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter, type Router } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import DeckIndexPage from '@/features/decks/DeckIndexPage.vue';

const {
  authState,
  apiGetMock,
  deleteDeckMock,
  fetchDeckTagsMock,
  fetchMyDeckMock,
  fetchMyDeckSummariesMock,
  fetchPublicDeckSummariesMock,
  intersectionState,
  updateDeckMock,
} = vi.hoisted(() => ({
  authState: {
    authenticated: true,
    canAccessStaffRoutes: false,
    user: { id: 'user-1' } as { id: string } | null,
  },
  apiGetMock: vi.fn(),
  deleteDeckMock: vi.fn(),
  fetchDeckTagsMock: vi.fn(),
  fetchMyDeckMock: vi.fn(),
  fetchMyDeckSummariesMock: vi.fn(),
  fetchPublicDeckSummariesMock: vi.fn(),
  intersectionState: {
    callback: null as null | ((entries: Array<{ isIntersecting: boolean }>) => void),
  },
  updateDeckMock: vi.fn(),
}));

vi.mock('@vueuse/core', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@vueuse/core')>();
  return {
    ...actual,
    useIntersectionObserver: (
      _target: unknown,
      callback: (entries: Array<{ isIntersecting: boolean }>) => void,
    ) => {
      intersectionState.callback = callback;
      return { stop: vi.fn() };
    },
  };
});

vi.mock('@/shared/api/client', () => ({
  api: {
    get: apiGetMock,
  },
}));

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/domain/decks/api', () => ({
  deleteDeck: deleteDeckMock,
  fetchDeckTags: fetchDeckTagsMock,
  fetchMyDeck: fetchMyDeckMock,
  fetchMyDeckSummaryPage: fetchMyDeckSummariesMock,
  fetchPublicDeckSummaryPage: fetchPublicDeckSummariesMock,
  updateDeck: updateDeckMock,
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock('@/domain/decks/composables/useDeckExport', () => ({
  useDeckExport: () => ({
    exportTtsDeck: vi.fn(),
  }),
}));

vi.mock('@/shared/components/app/AppPageHeader.vue', () => ({
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

vi.mock('@/shared/components/app/AppSelect.vue', () => ({
  default: defineComponent({
    props: {
      modelValue: { type: String, default: null },
      options: { type: Array, default: () => [] },
      placeholder: { type: String, default: undefined },
      placeholderDisabled: { type: Boolean, default: false },
    },
    emits: ['update:modelValue'],
    setup(props, { attrs, emit }) {
      return () =>
        h(
          'select',
          {
            ...attrs,
            value: props.modelValue ?? '',
            onChange: (event: Event) => {
              emit('update:modelValue', (event.target as HTMLSelectElement).value);
            },
          },
          [
            props.placeholder === undefined
              ? null
              : h('option', { value: '', disabled: props.placeholderDisabled }, props.placeholder),
            ...(props.options as Array<{ value: string; label: string }>).map((option) =>
              h('option', { value: option.value }, option.label),
            ),
          ],
        );
    },
  }),
}));

vi.mock('@/shared/components/modals/ConfirmModal.vue', () => ({
  default: defineComponent({
    setup() {
      return () => null;
    },
  }),
}));

vi.mock('@/domain/decks/components/DeckTagManagementModal.vue', () => ({
  default: defineComponent({
    props: {
      open: { type: Boolean, default: false },
      modelValue: { type: Array, default: () => [] },
      suggestedTypeLabels: { type: Array, default: () => [] },
    },
    emits: ['update:modelValue', 'update:suggestedTypeLabels', 'save', 'cancel', 'retry'],
    setup(props, { emit }) {
      return () => props.open
        ? h('div', { 'data-testid': 'tag-manager' }, [
            h('button', {
              'data-testid': 'tag-manager-change',
              onClick: () => {
                emit('update:modelValue', ['role-damage']);
                emit('update:suggestedTypeLabels', ['Tempo Burst']);
              },
            }, 'Change Tags'),
            h('button', { 'data-testid': 'tag-manager-save', onClick: () => emit('save') }, 'Save Tags'),
          ])
        : null;
    },
  }),
}));

vi.mock('@/shared/components/app/ExtraActionsMenu.vue', () => ({
  default: defineComponent({
    setup(_, { slots }) {
      return () => h('div', { 'data-testid': 'extra-actions-menu' }, slots.default?.({ close: () => undefined }));
    },
  }),
}));

vi.mock('@/features/decks/components/DeckBrowseFiltersPanel.vue', () => ({
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

vi.mock('@/domain/decks/components/DeckListCard.vue', () => ({
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
            props.mode === 'browse' ? slots['menu-actions']?.({ close: () => undefined }) : null,
          ],
        );
    },
  }),
}));

const deckRecord = {
  id: 'deck-1',
  name: 'Starter Deck',
  description: 'A test deck',
  difficulty: null,
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
  tags: [],
  pending_tag_suggestions: [],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const filtersPayload = {
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

const deckTagCatalog = {
  roles: [{ id: 'role-damage', key: 'damage', label: 'Damage', kind: 'role' as const }],
  types: [],
};

const deckPage = (
  results: Array<typeof deckRecord> = [deckRecord],
  overrides: Partial<{
    count: number;
    next_page: number | null;
    previous_page: number | null;
    page: number;
    page_size: number;
  }> = {},
) => ({
  count: results.length,
  next_page: null,
  next_cursor: overrides.next_page
    ? {
        created_at: results.at(-1)?.created_at ?? '2025-01-01T00:00:00Z',
        id: results.at(-1)?.id ?? 'deck-cursor',
      }
    : null,
  previous_page: null,
  page: 1,
  page_size: 10,
  snapshot_at: '2026-08-09T17:00:00Z',
  results,
  ...overrides,
});

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
    authState.canAccessStaffRoutes = false;
    authState.user = { id: 'user-1' };
    apiGetMock.mockResolvedValue({ data: filtersPayload });
    fetchDeckTagsMock.mockResolvedValue(deckTagCatalog);
    fetchMyDeckMock.mockResolvedValue(deckRecord);
    fetchMyDeckSummariesMock.mockResolvedValue(deckPage());
    fetchPublicDeckSummariesMock.mockResolvedValue(deckPage());
    intersectionState.callback = null;
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
    expect(mounted.container.querySelector('a[aria-label="Build a deck"]')?.textContent).toBe('Build a deck');

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

  test('appends the next deck page when the endless-scroll sentinel intersects', async () => {
    const nextDeck = {
      ...deckRecord,
      id: 'deck-2',
      name: 'Second Deck',
    };
    fetchPublicDeckSummariesMock
      .mockResolvedValueOnce(
      deckPage([deckRecord], {
        count: 11,
        next_page: 2,
      }),
      )
      .mockResolvedValueOnce(
        deckPage([nextDeck], {
          count: 11,
          page: 2,
          previous_page: 1,
        }),
      );
    const mounted = await mountPage('/decks');

    expect(fetchPublicDeckSummariesMock).toHaveBeenCalledWith(
      expect.any(URLSearchParams),
      1,
      10,
      null,
      null,
    );
    expect(mounted.container.textContent).toContain('Total 11');
    expect(mounted.container.textContent).not.toContain('Previous');

    intersectionState.callback?.([{ isIntersecting: true }]);
    await flushPage();

    expect(fetchPublicDeckSummariesMock).toHaveBeenLastCalledWith(
      expect.any(URLSearchParams),
      2,
      10,
      '2026-08-09T17:00:00Z',
      { created_at: '2025-01-01T00:00:00Z', id: 'deck-1' },
    );
    expect(mounted.container.textContent).toContain('Second Deck');
    expect(mounted.container.textContent).toContain('All 11 decks loaded.');

    mounted.unmount();
  });

  test('keeps loaded decks and offers a retry when loading the next page fails', async () => {
    const nextDeck = {
      ...deckRecord,
      id: 'deck-2',
      name: 'Recovered Deck',
    };
    fetchPublicDeckSummariesMock
      .mockResolvedValueOnce(deckPage([deckRecord], { count: 11, next_page: 2 }))
      .mockRejectedValueOnce(new Error('network failure'))
      .mockResolvedValueOnce(
        deckPage([nextDeck], {
          count: 11,
          page: 2,
          previous_page: 1,
        }),
      );
    const mounted = await mountPage('/decks');

    intersectionState.callback?.([{ isIntersecting: true }]);
    await flushPage();

    expect(mounted.container.textContent).toContain('Starter Deck');
    expect(mounted.container.textContent).toContain('Unable to load more decks.');
    const retryButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Retry',
    );
    retryButton?.click();
    await flushPage();

    expect(fetchPublicDeckSummariesMock).toHaveBeenLastCalledWith(
      expect.any(URLSearchParams),
      2,
      10,
      '2026-08-09T17:00:00Z',
      { created_at: '2025-01-01T00:00:00Z', id: 'deck-1' },
    );
    expect(mounted.container.textContent).toContain('Recovered Deck');

    mounted.unmount();
  });

  test('continues loading while the endless-scroll sentinel remains visible', async () => {
    fetchPublicDeckSummariesMock
      .mockResolvedValueOnce(deckPage([deckRecord], { count: 3, next_page: 2 }))
      .mockResolvedValueOnce(
        deckPage([{ ...deckRecord, id: 'deck-2', name: 'Second Deck' }], {
          count: 3,
          page: 2,
          previous_page: 1,
          next_page: 3,
        }),
      )
      .mockResolvedValueOnce(
        deckPage([{ ...deckRecord, id: 'deck-3', name: 'Third Deck' }], {
          count: 3,
          page: 3,
          previous_page: 2,
        }),
      );
    const mounted = await mountPage('/decks');

    intersectionState.callback?.([{ isIntersecting: true }]);
    await vi.waitFor(() => {
      expect(fetchPublicDeckSummariesMock).toHaveBeenCalledTimes(3);
    });
    await flushPage();

    expect(mounted.container.textContent).toContain('Second Deck');
    expect(mounted.container.textContent).toContain('Third Deck');
    expect(mounted.container.textContent).toContain('All 3 decks loaded.');

    mounted.unmount();
  });

  test('clears a superseded next-page loading state when the deck mode changes', async () => {
    const nextPageDeferred = createDeferred<ReturnType<typeof deckPage>>();
    fetchPublicDeckSummariesMock
      .mockResolvedValueOnce(deckPage([deckRecord], { count: 2, next_page: 2 }))
      .mockReturnValueOnce(nextPageDeferred.promise);
    fetchMyDeckSummariesMock.mockResolvedValueOnce(
      deckPage([{ ...deckRecord, id: 'owned-deck', name: 'Owned Deck' }]),
    );
    const mounted = await mountPage('/decks');

    intersectionState.callback?.([{ isIntersecting: true }]);
    await nextTick();
    await mounted.router.push('/my/decks');
    await flushPage();
    nextPageDeferred.resolve(
      deckPage([{ ...deckRecord, id: 'stale-deck', name: 'Stale Deck' }], {
        count: 2,
        page: 2,
        previous_page: 1,
      }),
    );
    await flushPage();

    expect(mounted.container.textContent).toContain('Owned Deck');
    expect(mounted.container.textContent).not.toContain('Stale Deck');
    expect(mounted.container.querySelector('.deck-loading-skeleton')).toBeNull();

    mounted.unmount();
  });

  test('ignores stale deck responses after switching between public and owned modes', async () => {
    const publicDeferred = createDeferred<ReturnType<typeof deckPage>>();
    fetchPublicDeckSummariesMock.mockReturnValueOnce(publicDeferred.promise);
    fetchMyDeckSummariesMock.mockResolvedValueOnce(
      deckPage([
        {
          ...deckRecord,
          id: 'owned-deck',
          name: 'Owned Deck',
        },
      ]),
    );
    const mounted = await mountPage('/decks');

    await mounted.router.push('/my/decks');
    await flushPage();

    publicDeferred.resolve(
      deckPage([
        {
          ...deckRecord,
          id: 'public-deck',
          name: 'Public Deck',
        },
      ]),
    );
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
    authState.user = null;
    const mounted = await mountPage('/decks');
    const links = Array.from(mounted.container.querySelectorAll<HTMLAnchorElement>('a'));

    expect(links.find((link) => link.textContent?.trim() === 'Public')).toBeUndefined();
    expect(links.find((link) => link.textContent?.trim() === 'My Decks')).toBeUndefined();
    expect(mounted.container.textContent).toContain('Search public decks');
    expect(fetchPublicDeckSummariesMock).toHaveBeenCalledTimes(1);
    expect(fetchMyDeckSummariesMock).not.toHaveBeenCalled();
    expect(mounted.container.querySelector('[aria-label="Manage deck tags"]')).toBeNull();

    mounted.unmount();
  });

  test('owned actions keep one edit action with extra actions and quick metadata selects', async () => {
    const mounted = await mountPage('/my/decks');
    const text = mounted.container.textContent ?? '';

    expect(text).toContain('Share');
    expect(text).toContain('TTS');
    expect(text).toContain('Delete');
    expect(text).toContain('Tags');
    expect(text).not.toContain('Copy Share Link');
    expect(text).not.toContain('Copy TTS');
    expect(text).not.toContain('Manage Tags');
    expect(mounted.container.querySelector('[aria-label="Manage deck tags"] svg')).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Playtest deck"] svg')).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Copy share link"] svg')).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Copy Mainboard TTS"] svg')).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Delete deck"] svg')).not.toBeNull();
    expect(text.match(/\bEdit\b/g) ?? []).toHaveLength(1);
    expect(mounted.container.querySelector('[aria-label="Deck visibility"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="deck-quick-metadata-controls"]')?.classList)
      .toContain('sm:grid-cols-2');
    const difficultySelect = mounted.container.querySelector<HTMLSelectElement>('[aria-label="Deck difficulty"]');
    expect(difficultySelect).not.toBeNull();
    expect(difficultySelect?.options[0]?.textContent).toBe('Difficulty');
    expect(difficultySelect?.options[0]?.disabled).toBe(true);
    expect(Array.from(difficultySelect?.options ?? []).map((option) => option.value)).toEqual([
      '',
      'easy',
      'medium',
      'hard',
    ]);

    mounted.unmount();
  });

  test('shows public deck editing to owners and staff but not unrelated users', async () => {
    const ownerPage = await mountPage('/decks');
    expect(ownerPage.container.querySelector('[aria-label="Edit deck"]')?.textContent).toContain('Edit');
    expect(ownerPage.container.querySelector('[aria-label="Manage deck tags"]')?.textContent).toContain('Tags');
    ownerPage.unmount();

    authState.user = { id: 'other-user' };
    const unrelatedPage = await mountPage('/decks');
    expect(unrelatedPage.container.querySelector('[aria-label="Edit deck"]')).toBeNull();
    expect(unrelatedPage.container.querySelector('[aria-label="Manage deck tags"]')).toBeNull();
    unrelatedPage.unmount();

    authState.canAccessStaffRoutes = true;
    const staffPage = await mountPage('/decks');
    expect(staffPage.container.querySelector('[aria-label="Edit deck"]')?.textContent).toContain('Edit');
    expect(staffPage.container.querySelector('[aria-label="Manage deck tags"]')?.textContent).toContain('Tags');
    staffPage.unmount();
  });

  test('hydrates and saves deck tags through the existing deck update API', async () => {
    const mounted = await mountPage('/decks');
    const manageButton = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Manage deck tags"]');
    manageButton?.click();
    await flushPage();

    expect(fetchMyDeckMock).toHaveBeenCalledWith('deck-1');
    mounted.container.querySelector<HTMLButtonElement>('[data-testid="tag-manager-change"]')?.click();
    await nextTick();
    mounted.container.querySelector<HTMLButtonElement>('[data-testid="tag-manager-save"]')?.click();
    await flushPage();

    expect(updateDeckMock).toHaveBeenCalledWith('deck-1', {
      tag_ids: ['role-damage'],
      suggested_type_labels: ['Tempo Burst'],
    });
    expect(fetchPublicDeckSummariesMock).toHaveBeenCalledTimes(2);

    mounted.unmount();
  });

  test('owned visibility changes send a partial deck patch', async () => {
    const mounted = await mountPage('/my/decks');
    const select = mounted.container.querySelector<HTMLSelectElement>('[aria-label="Deck visibility"]');
    if (!select) {
      throw new Error('expected visibility select');
    }

    select.value = 'private';
    select.dispatchEvent(new Event('change'));
    await flushPage();

    expect(updateDeckMock).toHaveBeenCalledWith('deck-1', { visibility: 'private' });
    expect(fetchMyDeckSummariesMock).toHaveBeenCalledTimes(2);

    mounted.unmount();
  });

  test('keeps confirmed metadata visible when the ordering refresh fails', async () => {
    updateDeckMock.mockResolvedValueOnce({ ...deckRecord, visibility: 'private' });
    fetchMyDeckSummariesMock
      .mockResolvedValueOnce(deckPage())
      .mockRejectedValueOnce(new Error('refresh failed'));
    const mounted = await mountPage('/my/decks');
    const select = mounted.container.querySelector<HTMLSelectElement>('[aria-label="Deck visibility"]');
    if (!select) {
      throw new Error('expected visibility select');
    }

    select.value = 'private';
    select.dispatchEvent(new Event('change'));
    await flushPage();

    expect(select.value).toBe('private');

    mounted.unmount();
  });

  test('owned difficulty changes send a partial deck patch without offering a clear option', async () => {
    const mounted = await mountPage('/my/decks');
    const select = mounted.container.querySelector<HTMLSelectElement>('[aria-label="Deck difficulty"]');
    if (!select) {
      throw new Error('expected difficulty select');
    }

    expect(Array.from(select.options).some((option) => option.value === 'null')).toBe(false);
    expect(select.options[0]?.disabled).toBe(true);

    select.value = 'medium';
    select.dispatchEvent(new Event('change'));
    await flushPage();

    expect(updateDeckMock).toHaveBeenCalledWith('deck-1', { difficulty: 'medium' });
    expect(fetchMyDeckSummariesMock).toHaveBeenCalledTimes(2);

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

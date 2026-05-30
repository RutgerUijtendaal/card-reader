/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter, type Router } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import DeckIndexPage from '@/modules/decks/DeckIndexPage.vue';

const {
  authState,
  apiGetMock,
  deleteDeckMock,
  fetchMyDecksMock,
  fetchPublicDecksMock,
  updateDeckMock,
} = vi.hoisted(() => ({
  authState: {
    authEnabled: true,
    authenticated: true,
  },
  apiGetMock: vi.fn(),
  deleteDeckMock: vi.fn(),
  fetchMyDecksMock: vi.fn(),
  fetchPublicDecksMock: vi.fn(),
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
  fetchMyDecks: fetchMyDecksMock,
  fetchPublicDecks: fetchPublicDecksMock,
  updateDeck: updateDeckMock,
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock('@/modules/decks/useDeckExport', () => ({
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
    setup(props) {
      return () =>
        h(
          'select',
          {
            value: props.modelValue ?? '',
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
      controller: { type: Object, required: true },
      description: { type: String, required: true },
      totalCount: { type: Number, required: true },
    },
    setup(props) {
      return () =>
        h('aside', [
          h('p', props.description),
          h('span', `Total ${props.totalCount}`),
          h('input', {
            'data-testid': 'card-query',
            value: (props.controller as { cardQuery: { value: string } }).cardQuery.value,
            onInput: (event: Event) => {
              (props.controller as { updateCardQuery: (value: string) => void }).updateCardQuery(
                (event.target as HTMLInputElement).value,
              );
            },
          }),
        ]);
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckListCard.vue', () => ({
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
    fetchMyDecksMock.mockResolvedValue([deckRecord]);
    fetchPublicDecksMock.mockResolvedValue([deckRecord]);
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  test('renders public mode on /decks and calls fetchPublicDecks', async () => {
    const mounted = await mountPage('/decks');

    expect(fetchPublicDecksMock).toHaveBeenCalledTimes(1);
    expect(fetchMyDecksMock).not.toHaveBeenCalled();
    expect(mounted.container.querySelector('[data-mode="browse"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-title-to="/decks/deck-1"]')).not.toBeNull();
    expect(mounted.container.textContent).toContain('Filter public decks');

    mounted.unmount();
  });

  test('renders deck skeleton cards while deck filters are loading', async () => {
    apiGetMock.mockReturnValue(new Promise(() => undefined));
    const mounted = await mountPage('/decks');

    expect(mounted.container.querySelectorAll('.deck-loading-skeleton')).toHaveLength(4);
    expect(mounted.container.textContent).not.toContain('Loading decks');

    mounted.unmount();
  });

  test('renders owned mode on /my/decks and calls fetchMyDecks', async () => {
    const mounted = await mountPage('/my/decks');

    expect(fetchMyDecksMock).toHaveBeenCalledTimes(1);
    expect(fetchPublicDecksMock).not.toHaveBeenCalled();
    expect(mounted.container.querySelector('[data-mode="owned"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-title-to="/my/decks/deck-1"]')).not.toBeNull();
    expect(mounted.container.textContent).toContain('Filter your decks');

    mounted.unmount();
  });

  test('tabs link to public and owned deck routes', async () => {
    const mounted = await mountPage('/my/decks?card_q=Blade');
    const links = Array.from(mounted.container.querySelectorAll<HTMLAnchorElement>('a'));

    expect(
      links.some((link) => link.textContent?.trim() === 'Public' && link.getAttribute('href') === '/decks?card_q=Blade'),
    ).toBe(true);
    expect(
      links.some(
        (link) => link.textContent?.trim() === 'My Decks' && link.getAttribute('href') === '/my/decks?card_q=Blade',
      ),
    ).toBe(true);

    mounted.unmount();
  });

  test('owned actions keep one edit action with extra actions and visibility select', async () => {
    const mounted = await mountPage('/my/decks');
    const text = mounted.container.textContent ?? '';

    expect(text).toContain('Copy Share Link');
    expect(text).toContain('Export TTS');
    expect(text).toContain('Delete');
    expect(text.match(/\bEdit\b/g) ?? []).toHaveLength(1);
    expect(mounted.container.querySelector('select')).not.toBeNull();

    mounted.unmount();
  });

  test.each([
    ['/decks', fetchPublicDecksMock],
    ['/my/decks', fetchMyDecksMock],
  ])('passes route filters to API params for %s', async (path, fetchMock) => {
    const mounted = await mountPage(`${path}?card_q=Blade`);

    expect(lastSearchParams(fetchMock).get('card_q')).toBe('Blade');

    mounted.unmount();
  });

  test.each(['/decks', '/my/decks'])('filter input updates the %s route query', async (path) => {
    vi.useFakeTimers();
    const mounted = await mountPage(path);
    const input = mounted.container.querySelector<HTMLInputElement>('[data-testid="card-query"]');
    if (!input) {
      throw new Error('expected card filter input');
    }

    input.value = 'Blade';
    input.dispatchEvent(new Event('input'));
    await nextTick();
    await vi.advanceTimersByTimeAsync(300);
    await flushPage();

    expect(mounted.router.currentRoute.value.query.card_q).toBe('Blade');

    mounted.unmount();
  });
});

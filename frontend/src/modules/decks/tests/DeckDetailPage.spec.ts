/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import DeckDetailPage from '@/modules/decks/DeckDetailPage.vue';

const { fetchDeckDetailMock, fetchMyDeckMock, apiGetMock } = vi.hoisted(() => ({
  fetchDeckDetailMock: vi.fn(),
  fetchMyDeckMock: vi.fn(),
  apiGetMock: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  api: {
    get: apiGetMock,
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/modules/auth/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'user-1' },
  }),
}));

vi.mock('@/modules/decks/api', () => ({
  fetchDeckDetail: fetchDeckDetailMock,
  fetchMyDeck: fetchMyDeckMock,
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
          slots.titleMeta?.(),
          slots.actions?.(),
        ]);
    },
  }),
}));

vi.mock('@/components/cards/CardGalleryItem.vue', () => ({
  default: defineComponent({
    props: {
      card: { type: Object, required: true },
    },
    setup(props, { slots }) {
      return () =>
        h(
          'article',
          { 'data-testid': `deck-card-${(props.card as { id: string }).id}` },
          [
            h('span', (props.card as { name: string }).name),
            slots.overlay?.(),
          ],
        );
    },
  }),
}));

vi.mock('@/components/cards/CardSortMenu.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('div', { 'data-testid': 'sort-menu' });
    },
  }),
}));

vi.mock('@/components/cards/GalleryOptionsMenu.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('div', { 'data-testid': 'gallery-options-menu' });
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckManaCurve.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('div', { 'data-testid': 'mana-curve' });
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckCardCountBadge.vue', () => ({
  default: defineComponent({
    props: {
      quantity: { type: Number, required: true },
    },
    setup(props) {
      return () => h('span', { 'data-testid': 'count-badge' }, String(props.quantity));
    },
  }),
}));

const buildCard = (
  id: string,
  name: string,
  types: Array<{ key: string; label: string }>,
) => ({
  id,
  key: id,
  label: name,
  result_type: 'card' as const,
  image_url: null,
  name,
  mana_cost: '',
  mana_symbols: [],
  mana_value: 1,
  attack: null,
  health: null,
  type_line: '',
  rules_text: '',
  confidence: 1,
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-01T00:00:00.000Z',
  keywords: [],
  tags: [],
  symbols: [],
  types,
});

const deckRecord = {
  id: 'deck-1',
  name: 'Grouped Deck',
  description: null,
  visibility: 'public' as const,
  owner: {
    id: 'user-1',
    username: 'owner',
  },
  hero_card: buildCard('hero', 'Hero', []),
  mainboard: {
    total_cards: 4,
    unique_cards: 4,
    entries: [
      { quantity: 1, card: buildCard('creature', 'Creature Card', [{ key: 'creature', label: 'Creature' }]) },
      { quantity: 1, card: buildCard('spell', 'Spell Card', [{ key: 'spell', label: 'Spell' }]) },
      { quantity: 1, card: buildCard('blank', 'Blank Card', []) },
      { quantity: 1, card: buildCard('mana', 'Mana Card', [{ key: 'mana', label: 'Mana' }]) },
    ],
  },
  sideboards: [
    {
      id: 'side-1',
      name: 'Sideboard',
      total_cards: 1,
      unique_cards: 1,
      entries: [
        { quantity: 1, card: buildCard('attachment', 'Attachment Card', [{ key: 'attachment', label: 'Attachment' }]) },
      ],
    },
  ],
  totals: {
    overall_total_cards: 5,
    overall_unique_cards: 5,
    mainboard_total_cards: 4,
    mainboard_unique_cards: 4,
  },
  status: {
    is_valid: true,
    label: 'Ready',
    issues: [],
  },
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-01T00:00:00.000Z',
};

const filtersPayload = {
  keywords: [],
  tags: [],
  symbols: [],
  types: [
    { id: 'type-mana', key: 'mana', label: 'Mana', linked_card_count: 99 },
    { id: 'type-creature', key: 'creature', label: 'Creature', linked_card_count: 3 },
    { id: 'type-spell', key: 'spell', label: 'Spell', linked_card_count: 5 },
    { id: 'type-attachment', key: 'attachment', label: 'Attachment', linked_card_count: 1 },
  ],
};

const createDeferred = <T,>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
};

const mountPage = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/decks/:id', component: DeckDetailPage },
      { path: '/cards/:id', component: { template: '<div />' } },
      { path: '/decks', component: { template: '<div />' } },
      { path: '/my/decks', component: { template: '<div />' } },
      { path: '/my/decks/:id/edit', component: { template: '<div />' } },
    ],
  });
  await router.push('/decks/deck-1');
  await router.isReady();

  const app = createApp(DeckDetailPage);
  app.use(router);
  app.mount(container);
  await nextTick();
  await Promise.resolve();
  await nextTick();

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const readTypeGroupKeys = (container: HTMLElement): string[] =>
  Array.from(container.querySelectorAll('[data-testid="deck-type-group"]')).map(
    (element) => element.getAttribute('data-type-group-key') ?? '',
  );

describe('DeckDetailPage type grouping', () => {
  beforeEach(() => {
    localStorage.clear();
    fetchDeckDetailMock.mockResolvedValue(deckRecord);
    fetchMyDeckMock.mockResolvedValue(deckRecord);
    apiGetMock.mockResolvedValue({ data: filtersPayload });
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('renders mainboard cards grouped by type order by default', async () => {
    const mounted = await mountPage();

    expect(readTypeGroupKeys(mounted.container)).toEqual(['spell', 'creature', 'untyped', 'mana']);
    expect(mounted.container.querySelector<HTMLInputElement>('input[type="checkbox"]')?.checked).toBe(true);
    expect(mounted.container.querySelectorAll('[data-testid^="deck-card-"]')).toHaveLength(4);

    mounted.unmount();
  });

  test('renders a deck-detail-shaped skeleton while loading initial data', async () => {
    const deferredDeck = createDeferred<typeof deckRecord>();
    fetchDeckDetailMock.mockReturnValueOnce(deferredDeck.promise);
    const mounted = await mountPage();

    expect(mounted.container.querySelector('[aria-label="Loading deck detail"]')).not.toBeNull();
    expect(mounted.container.querySelector('.page-card')).toBeNull();
    expect(mounted.container.textContent).not.toContain('Grouped Deck');
    expect(mounted.container.querySelectorAll('[data-testid="deck-loading-type-group"]')).toHaveLength(2);

    deferredDeck.resolve(deckRecord);
    await deferredDeck.promise;
    await Promise.resolve();
    await Promise.resolve();
    await nextTick();

    expect(mounted.container.querySelector('[aria-label="Loading deck detail"]')).toBeNull();
    expect(mounted.container.textContent).toContain('Grouped Deck');

    mounted.unmount();
  });

  test('renders a flat card-grid skeleton while loading when grouping is disabled', async () => {
    localStorage.setItem('card-reader.deck-detail-group-by-type', 'false');
    const deferredDeck = createDeferred<typeof deckRecord>();
    fetchDeckDetailMock.mockReturnValueOnce(deferredDeck.promise);
    const mounted = await mountPage();

    expect(mounted.container.querySelector('[aria-label="Loading deck detail"]')).not.toBeNull();
    expect(mounted.container.querySelectorAll('[data-testid="deck-loading-type-group"]')).toHaveLength(0);

    deferredDeck.resolve(deckRecord);
    await deferredDeck.promise;
    await Promise.resolve();
    await Promise.resolve();
    await nextTick();

    mounted.unmount();
  });

  test('renders one ungrouped card grid when grouping is disabled', async () => {
    localStorage.setItem('card-reader.deck-detail-group-by-type', 'false');
    const mounted = await mountPage();

    expect(readTypeGroupKeys(mounted.container)).toEqual([]);
    expect(mounted.container.querySelector<HTMLInputElement>('input[type="checkbox"]')?.checked).toBe(false);
    expect(mounted.container.querySelectorAll('[data-testid^="deck-card-"]')).toHaveLength(4);

    mounted.unmount();
  });

  test('groups the active sideboard instead of all deck entries', async () => {
    localStorage.setItem('card-reader.deck-detail-group-by-type', 'true');
    const mounted = await mountPage();
    const sideboardButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Sideboard'),
    );
    if (!(sideboardButton instanceof HTMLButtonElement)) {
      throw new Error('expected sideboard tab');
    }

    sideboardButton.click();
    await nextTick();

    expect(readTypeGroupKeys(mounted.container)).toEqual(['attachment']);
    expect(mounted.container.textContent).toContain('Attachment Card');
    expect(mounted.container.textContent).not.toContain('Spell Card');

    mounted.unmount();
  });
});

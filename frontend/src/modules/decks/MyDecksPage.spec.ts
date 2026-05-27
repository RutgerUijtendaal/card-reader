/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import MyDecksPage from '@/modules/decks/MyDecksPage.vue';

const { fetchMyDecks } = vi.hoisted(() => ({
  fetchMyDecks: vi.fn(),
}));

vi.mock('@/modules/decks/api', () => ({
  deleteDeck: vi.fn(),
  fetchMyDecks,
  updateDeck: vi.fn(),
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
        h('section', [
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
    emits: ['update:model-value'],
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

vi.mock('@/modules/decks/components/DeckListCard.vue', () => ({
  default: defineComponent({
    props: {
      deck: { type: Object, required: true },
    },
    setup(props, { slots }) {
      return () =>
        h('article', [
          h('h2', (props.deck as { name: string }).name),
          slots.actions?.(),
        ]);
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

const mountPage = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/my/decks', component: MyDecksPage },
      { path: '/my/decks/:id', component: { template: '<div />' } },
      { path: '/my/decks/:id/edit', component: { template: '<div />' } },
      { path: '/my/decks/new', component: { template: '<div />' } },
      { path: '/decks', component: { template: '<div />' } },
    ],
  });
  await router.push('/my/decks');
  await router.isReady();

  const app = createApp(MyDecksPage);
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

describe('MyDecksPage', () => {
  beforeEach(() => {
    fetchMyDecks.mockReset();
    fetchMyDecks.mockResolvedValue([deckRecord]);
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('keeps edit as a primary action instead of duplicating it in the extra actions menu', async () => {
    const mounted = await mountPage();
    const text = mounted.container.textContent ?? '';

    expect(text).toContain('Copy Share Link');
    expect(text).toContain('Export TTS');
    expect(text).toContain('Delete');
    expect(text.match(/\bEdit\b/g) ?? []).toHaveLength(1);

    mounted.unmount();
  });
});

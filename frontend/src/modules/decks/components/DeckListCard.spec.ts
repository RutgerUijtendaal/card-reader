import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test } from 'vitest';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';
import type { DeckRecord } from '@/modules/decks/types';

const buildDeck = (): DeckRecord => ({
  id: 'deck-1',
  name: 'Azure Tempo',
  description: 'Pressure early, then pivot into efficient trades.',
  visibility: 'public',
  owner: {
    id: 'user-1',
    username: 'maitys',
  },
  hero_card: {
    id: 'card-1',
    key: 'card-1',
    label: 'Azure Hero',
    is_hero: true,
    template_id: 'template-1',
    version_id: 'version-1',
    version_number: 1,
    previous_version_id: null,
    is_latest: true,
    name: 'Azure Hero',
    type_line: 'Hero',
    mana_cost: '3',
    mana_symbols: [],
    mana_value: 3,
    attack: null,
    health: null,
    rules_text: '',
    confidence: 1,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    keywords: [],
    tags: [],
    symbols: [],
    types: [],
    image_url: null,
    result_type: 'card',
  },
  mainboard: {
    total_cards: 40,
    unique_cards: 24,
    entries: [
      {
        quantity: 4,
        card: {
          id: 'card-2',
          key: 'card-2',
          label: 'Spark Mage',
          is_hero: false,
          template_id: 'template-1',
          version_id: 'version-1',
          version_number: 1,
          previous_version_id: null,
          is_latest: true,
          name: 'Spark Mage',
          type_line: 'Unit',
          mana_cost: '2',
          mana_symbols: [],
          mana_value: 2,
          attack: 2,
          health: 2,
          rules_text: '',
          confidence: 1,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
          keywords: [],
          tags: [],
          symbols: [],
          types: [],
          image_url: null,
          result_type: 'card',
        },
      },
    ],
  },
  sideboards: [
    {
      id: 'side-1',
      name: 'Tech',
      total_cards: 8,
      unique_cards: 6,
      entries: [],
    },
  ],
  totals: {
    overall_total_cards: 48,
    overall_unique_cards: 30,
    mainboard_total_cards: 40,
    mainboard_unique_cards: 24,
  },
  status: {
    is_valid: true,
    label: 'Ready',
    issues: [],
  },
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
});

const mountDeckListCard = async (mode: 'browse' | 'owned') => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/decks', component: { template: '<div />' } },
      { path: '/decks/:id', component: { template: '<div />' } },
      { path: '/my/decks/:id', component: { template: '<div />' } },
    ],
  });
  await router.push('/decks');
  await router.isReady();

  const app = createApp(DeckListCard, {
    deck: buildDeck(),
    mode,
    titleTo: mode === 'browse' ? '/decks/deck-1' : '/my/decks/deck-1',
  });
  app.use(router);
  app.mount(container);
  await nextTick();

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('DeckListCard', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders fold-down browse metadata and moves the curve into the detail area', async () => {
    const mounted = await mountDeckListCard('browse');
    const text = mounted.container.textContent ?? '';

    expect(mounted.container.querySelector('.deck-list-card-browse-details')).not.toBeNull();
    expect(text).toContain('Mainboard Curve');
    expect(text).toContain('Mainboard');
    expect(text).toContain('All Boards');
    expect(text).toContain('Side Decks');
    expect(text).toContain('Status');

    mounted.unmount();
  });

  test('keeps owned deck cards on the non-expanded management layout', async () => {
    const mounted = await mountDeckListCard('owned');
    const text = mounted.container.textContent ?? '';

    expect(mounted.container.querySelector('.deck-list-card-browse-details')).toBeNull();
    expect(text).toContain('Hero');
    expect(text).toContain('Total / Main');
    expect(text).not.toContain('Mainboard Curve');

    mounted.unmount();
  });
});

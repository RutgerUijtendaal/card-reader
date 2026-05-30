import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardDeckReferencesPanel from '@/modules/card-detail/components/CardDeckReferencesPanel.vue';
import type { CardDeckReferenceSummary } from '@/modules/card-detail/types';
import type { DeckRecord } from '@/modules/decks/types';

vi.mock('@/modules/decks/useDeckExport', () => ({
  useDeckExport: () => ({
    exportTtsDeck: vi.fn(),
  }),
}));

vi.mock('vue-sonner', () => ({
  toast: {
    success: vi.fn(),
  },
}));

const buildDeck = (
  id: string,
  name: string,
  ownerId: string,
  cardReference: CardDeckReferenceSummary['card_reference'],
): CardDeckReferenceSummary => ({
  id,
  name,
  description: null,
  visibility: ownerId === 'user-1' ? 'private' : 'public',
  owner: { id: ownerId, username: ownerId === 'user-1' ? 'owner' : 'other' },
  hero_card: {
    id: 'hero-card',
    key: 'hero-card',
    label: 'Hero Card',
    is_hero: true,
    template_id: 'template-1',
    version_id: 'version-1',
    version_number: 1,
    previous_version_id: null,
    is_latest: true,
    name: 'Hero Card',
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
    unique_cards: 12,
    entries: [],
  },
  sideboards: [],
  totals: {
    overall_total_cards: 40,
    overall_unique_cards: 12,
    mainboard_total_cards: 40,
    mainboard_unique_cards: 12,
  },
  status: {
    is_valid: true,
    label: 'Ready',
    issues: [],
  },
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  card_reference: cardReference,
} satisfies DeckRecord & CardDeckReferenceSummary);

const deckReferences: CardDeckReferenceSummary[] = [
  buildDeck('deck-owned', 'Owned Control', 'user-1', {
    is_hero: false,
    mainboard_quantity: 2,
    sideboard_quantity: 1,
  }),
  buildDeck('deck-public', 'Public Aggro', 'user-2', {
    is_hero: true,
    mainboard_quantity: 0,
    sideboard_quantity: 0,
  }),
];

const mountPanel = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/decks/:id', component: { template: '<div />' } },
      { path: '/my/decks/:id', component: { template: '<div />' } },
    ],
  });
  await router.push('/decks/deck-public');
  await router.isReady();

  const app = createApp(CardDeckReferencesPanel, {
    deckReferences,
    currentUserId: 'user-1',
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

describe('CardDeckReferencesPanel', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('shows deck count, deck locations, and inclusion roles', async () => {
    const mounted = await mountPanel();

    expect(mounted.container.textContent).toContain('Card is in 2 decks');
    expect(mounted.container.textContent).toContain('Owned Control');
    expect(mounted.container.textContent).toContain('Mainboard x2');
    expect(mounted.container.textContent).toContain('Sideboard x1');
    expect(mounted.container.textContent).toContain('Public Aggro');
    expect(mounted.container.textContent).toContain('Includes as hero');
    expect(mounted.container.querySelector('[data-navigation-target="/my/decks/deck-owned"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-navigation-target="/decks/deck-public"]')).not.toBeNull();

    mounted.unmount();
  });
});

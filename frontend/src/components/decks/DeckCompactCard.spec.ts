import { createApp, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckCompactCard from '@/components/decks/DeckCompactCard.vue';
import type { DeckSummaryRecord } from '@/modules/decks/types';

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

const buildDeck = (overrides: Partial<DeckSummaryRecord> = {}): DeckSummaryRecord => ({
  id: 'deck-1',
  name: 'Azure Tempo',
  description: 'Pressure early.',
  visibility: 'public',
  owner: {
    id: 'user-1',
    username: 'maitys',
  },
  hero_card: {
    id: 'hero-1',
    key: 'hero-1',
    label: 'Azure Hero',
    image_url: '/media/cards/hero.png',
    name: 'Azure Hero',
    symbols: [
      {
        id: 'sym-1',
        key: 'fire',
        label: 'Fire',
        symbol_type: 'affinity',
        text_token: '{F}',
        asset_url: null,
      },
    ],
  },
  mainboard: {
    total_cards: 40,
    unique_cards: 24,
  },
  sideboard_count: 1,
  status: {
    is_valid: true,
    label: 'Ready',
    deprecated_card_count: 0,
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

const mountDeckCompactCard = async (
  options: {
    deck?: DeckSummaryRecord;
    mode?: 'browse' | 'owned';
    selected?: boolean;
    surface?: 'default' | 'playtester';
    onSelect?: () => void;
  } = {},
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const app = createApp({
    render: () => h(DeckCompactCard, {
      deck: options.deck ?? buildDeck(),
      mode: options.mode ?? 'browse',
      selected: options.selected,
      surface: options.surface,
      onSelect: options.onSelect,
    }),
  });
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

describe('DeckCompactCard', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders public deck identity with hero art, owner pill, summary, and affinity symbols', async () => {
    const mounted = await mountDeckCompactCard();
    const text = mounted.container.textContent ?? '';
    const image = mounted.container.querySelector<HTMLImageElement>('.deck-compact-card-art-image');

    expect(mounted.container.querySelector('.deck-compact-card-browse')).not.toBeNull();
    expect(image?.src).toContain('/media/cards/hero.png');
    expect(image?.alt).toBe('Azure Hero');
    expect(text).toContain('Azure Tempo');
    expect(text).toContain('Maitys');
    expect(text).toContain('Hero: Azure Hero');
    expect(text).toContain('Maindeck 40 · 24 unique · 1 sideboard');
    expect(text).toContain('{F}');
    expect(text).not.toContain('Pressure early.');
    expect(text).not.toContain('Updated');

    mounted.unmount();
  });

  test('renders owned deck visibility and deprecated warning', async () => {
    const mounted = await mountDeckCompactCard({
      mode: 'owned',
      deck: buildDeck({
        visibility: 'private',
        status: {
          is_valid: true,
          label: 'Ready',
          deprecated_card_count: 2,
        },
      }),
    });
    const text = mounted.container.textContent ?? '';

    expect(mounted.container.querySelector('.deck-compact-card-owned')).not.toBeNull();
    expect(text).toContain('Private');
    expect(text).toContain('2');

    mounted.unmount();
  });

  test('renders fallback art and no sideboards summary', async () => {
    const mounted = await mountDeckCompactCard({
      deck: buildDeck({
        hero_card: {
          ...buildDeck().hero_card,
          image_url: null,
          symbols: [],
        },
        sideboard_count: 0,
      }),
    });
    const text = mounted.container.textContent ?? '';

    expect(mounted.container.querySelector('.deck-compact-card-art-fallback')).not.toBeNull();
    expect(mounted.container.querySelector('.deck-compact-card-art-image')).toBeNull();
    expect(text).toContain('Maindeck 40 · 24 unique · No sideboards');
    expect(text).not.toContain('{F}');

    mounted.unmount();
  });

  test('emits select on click and keyboard activation with selected state', async () => {
    const onSelect = vi.fn();
    const mounted = await mountDeckCompactCard({ selected: true, onSelect });
    const card = mounted.container.querySelector<HTMLButtonElement>('[data-testid="deck-compact-card"]');
    if (!card) {
      throw new Error('expected compact deck card');
    }

    expect(card.getAttribute('aria-pressed')).toBe('true');
    expect(card.classList.contains('deck-compact-card-selected')).toBe(true);

    card.click();
    card.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
    card.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true, cancelable: true }));
    await nextTick();

    expect(onSelect).toHaveBeenCalledTimes(3);

    mounted.unmount();
  });

  test('applies playtester surface class when requested', async () => {
    const mounted = await mountDeckCompactCard({ surface: 'playtester', selected: true });
    const card = mounted.container.querySelector<HTMLButtonElement>('[data-testid="deck-compact-card"]');
    if (!card) {
      throw new Error('expected compact deck card');
    }

    expect(card.classList.contains('deck-compact-card-playtester')).toBe(true);
    expect(card.classList.contains('deck-compact-card-selected')).toBe(true);

    mounted.unmount();
  });
});

import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';
import type { DeckRecord } from '@/modules/decks/types';

const { exportTtsDeckMock, toastSuccessMock } = vi.hoisted(() => ({
  exportTtsDeckMock: vi.fn<(...args: unknown[]) => Promise<void>>().mockResolvedValue(undefined),
  toastSuccessMock: vi.fn(),
}));

vi.mock('@/modules/decks/useDeckExport', () => ({
  useDeckExport: () => ({
    exportTtsDeck: exportTtsDeckMock,
  }),
}));

vi.mock('vue-sonner', () => ({
  toast: {
    success: toastSuccessMock,
  },
}));

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
    types: [],
    image_url: '/media/cards/hero.png',
    result_type: 'card',
  },
  mainboard: {
    total_cards: 40,
    unique_cards: 24,
    entries: [],
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
    router,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('DeckListCard', () => {
  beforeEach(() => {
    exportTtsDeckMock.mockClear();
    toastSuccessMock.mockClear();
    vi.stubGlobal('navigator', {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.unstubAllGlobals();
  });

  test('renders browse mode as a static horizontal card without foldout controls', async () => {
    const mounted = await mountDeckListCard('browse');
    const text = mounted.container.textContent ?? '';

    expect(mounted.container.querySelector('.deck-list-card-browse')).not.toBeNull();
    expect(mounted.container.querySelector('.deck-list-card-description')).not.toBeNull();
    expect(mounted.container.querySelector('button[aria-label="Toggle deck details"]')).toBeNull();
    expect(mounted.container.querySelector('.deck-list-card-browse-details')).toBeNull();
    expect(text).toContain('Azure Tempo');
    expect(text).toContain('Hero: Azure Hero');
    expect(text).toContain('maitys');
    expect(text).toContain('Maindeck 40 · 24 unique · 1 sideboard');
    expect(text).toContain('{F}');
    expect(text).toContain('Pressure early, then pivot into efficient trades.');
    expect(text).not.toContain('Mainboard 40 · 24 unique · 1 sideboard');
    expect(text).toContain('Updated');

    mounted.unmount();
  });

  test('keeps owned deck cards on the management layout', async () => {
    const mounted = await mountDeckListCard('owned');
    const text = mounted.container.textContent ?? '';

    expect(mounted.container.querySelector('.deck-list-card-owned')).not.toBeNull();
    expect(text).toContain('Azure Tempo');
    expect(text).toContain('Public');
    expect(text).toContain('Hero: Azure Hero');
    expect(text).toContain('Maindeck 40 · 24 unique · 1 sideboard');
    expect(text).toContain('{F}');
    expect(text).toContain('Updated');

    mounted.unmount();
  });

  test('browse card keeps the expected navigation target', async () => {
    const mounted = await mountDeckListCard('browse');
    const card = mounted.container.querySelector('.deck-list-card-browse');

    expect(card).not.toBeNull();
    expect(card?.getAttribute('data-navigation-target')).toBe('/decks/deck-1');

    mounted.unmount();
  });

  test.each([
    ['browse', '.deck-list-card-browse', '/decks/deck-1'],
    ['owned', '.deck-list-card-owned', '/my/decks/deck-1'],
  ] as const)('clickable %s deck cards remain keyboard focusable links', async (mode, selector, target) => {
    const mounted = await mountDeckListCard(mode);
    const card = mounted.container.querySelector<HTMLElement>(selector);
    const pushSpy = vi.spyOn(mounted.router, 'push');

    expect(card?.getAttribute('role')).toBe('link');
    expect(card?.getAttribute('tabindex')).toBe('0');

    card?.focus();
    card?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true, cancelable: true }));
    await nextTick();

    expect(pushSpy).toHaveBeenCalledWith(target);

    mounted.unmount();
  });

  test('copy share link action writes to clipboard without navigating the card', async () => {
    const mounted = await mountDeckListCard('browse');
    const menuTrigger = mounted.container.querySelector('button[aria-label="Open deck actions"]');
    const clipboardWriteText = navigator.clipboard.writeText as ReturnType<typeof vi.fn>;

    menuTrigger?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await nextTick();

    const copyButton = document.body.querySelector('button');
    const matchingButtons = Array.from(document.body.querySelectorAll('button'));
    const copyShareButton = matchingButtons.find((button) => button.textContent?.includes('Copy Share Link'));

    expect(copyButton).not.toBeNull();
    expect(copyShareButton).not.toBeNull();

    copyShareButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await nextTick();

    expect(clipboardWriteText).toHaveBeenCalledWith(expect.stringContaining('/decks/deck-1'));
    expect(toastSuccessMock).toHaveBeenCalledWith('Share link copied.');
    expect(mounted.router.currentRoute.value.fullPath).toBe('/decks');

    mounted.unmount();
  });

  test('export tts action reuses the deck export helper without navigating the card', async () => {
    const mounted = await mountDeckListCard('browse');
    const menuTrigger = mounted.container.querySelector('button[aria-label="Open deck actions"]');

    menuTrigger?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await nextTick();

    const exportButton = Array.from(document.body.querySelectorAll('button')).find((button) => button.textContent?.includes('Export TTS'));

    expect(exportButton).not.toBeNull();

    exportButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await nextTick();

    expect(exportTtsDeckMock).toHaveBeenCalledWith('deck-1', 'Azure Tempo');
    expect(mounted.router.currentRoute.value.fullPath).toBe('/decks');

    mounted.unmount();
  });
});

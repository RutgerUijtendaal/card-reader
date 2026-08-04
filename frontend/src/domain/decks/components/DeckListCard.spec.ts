import { createApp, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import DeckListCard from '@/domain/decks/components/DeckListCard.vue';
import type { DeckRecord } from '@/domain/decks/types';

const { exportTtsDeckMock, toastSuccessMock } = vi.hoisted(() => ({
  exportTtsDeckMock: vi.fn<(...args: unknown[]) => Promise<void>>().mockResolvedValue(undefined),
  toastSuccessMock: vi.fn(),
}));

vi.mock('@/domain/decks/composables/useDeckExport', () => ({
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
  long_description: null,
  difficulty: 'hard',
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
  tags: [
    { id: 'role-damage', kind: 'role', key: 'damage', label: 'Damage' },
    { id: 'type-armor', kind: 'type', key: 'armor', label: 'Armor' },
  ],
  pending_tag_suggestions: [
    {
      id: 'suggestion-tempo',
      label: 'Tempo Burst',
      normalized_value: 'tempo burst',
      kind: 'type',
      status: 'pending',
    },
  ],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
});

const mountDeckListCard = async (
  mode: 'browse' | 'owned',
  options: { customActions?: boolean; menuActions?: boolean; deck?: Partial<DeckRecord> } = {},
) => {
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

  const app = createApp({
    render: () => h(
      DeckListCard,
      {
        deck: { ...buildDeck(), ...options.deck },
        mode,
        titleTo: mode === 'browse' ? '/decks/deck-1' : '/my/decks/deck-1',
      },
      {
        ...(options.customActions
          ? { actions: () => h('button', { class: 'custom-action', type: 'button' }, 'Custom Action') }
          : {}),
        ...(options.menuActions
          ? {
              'menu-actions': ({ close }: { close: () => void }) => h(
                'button',
                { class: 'manage-tags-action', type: 'button', 'aria-label': 'Manage deck tags', onClick: close },
                [h('svg', { class: 'h-4 w-4' }), 'Tags'],
              ),
            }
          : {}),
      },
    ),
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
    const footerText = mounted.container.querySelector('.deck-list-card-footer-meta')?.textContent ?? '';

    expect(mounted.container.querySelector('.deck-list-card-browse')).not.toBeNull();
    expect(mounted.container.querySelector('.deck-list-card-description')).not.toBeNull();
    expect(mounted.container.querySelector('.deck-list-card-footer')).not.toBeNull();
    expect(mounted.container.querySelector('img[alt="Azure Hero"]')).not.toBeNull();
    expect(mounted.container.querySelector('button[aria-label="Toggle deck details"]')).toBeNull();
    expect(mounted.container.querySelector('.deck-list-card-browse-details')).toBeNull();
    expect(text).toContain('Azure Tempo');
    expect(text).toContain('Maitys');
    expect(text).not.toContain('maitys');
    expect(mounted.container.querySelector('.deck-list-card-title-row')?.classList).toContain('justify-between');
    expect(mounted.container.querySelector('.deck-list-card-title-row h3')?.classList).toContain('text-xl');
    expect(mounted.container.querySelector('.deck-list-card-title-row h3')?.classList).toContain('truncate');
    expect(mounted.container.querySelector('.deck-list-card-title-pill')?.classList).toContain('theme-pill-neutral');
    expect(text).toContain('{F}');
    expect(text).toContain('Pressure early, then pivot into efficient trades.');
    expect(text).toContain('Damage');
    expect(text).toContain('Armor');
    expect(mounted.container.querySelector('.deck-list-card-title-row')?.textContent).not.toContain('Damage');
    expect(mounted.container.querySelector('.deck-list-card-title-row')?.textContent).not.toContain('Armor');
    expect(mounted.container.querySelector('.deck-list-card-tags')?.textContent).toContain('Damage');
    expect(mounted.container.querySelector('.deck-list-card-tags')?.textContent).toContain('Armor');
    expect(mounted.container.querySelector('.deck-list-card-main .deck-list-card-tags')).toBeNull();
    expect(mounted.container.querySelector('.deck-list-card-tags-region .deck-list-card-tags')).not.toBeNull();
    expect(mounted.container.querySelector('.deck-list-card-tags-region')?.nextElementSibling?.classList).toContain('deck-list-card-footer');
    expect(text).not.toContain('Tempo Burst');
    expect(text).not.toContain('Maindeck 40 · 24 unique · 1 sideboard');
    expect(text).not.toContain('Mainboard 40 · 24 unique · 1 sideboard');
    expect(footerText).not.toContain('Azure Hero');
    expect(footerText).toContain('Maindeck 40');
    expect(footerText).toContain('Unique 24');
    expect(footerText).toContain('Sideboards 1');
    expect(footerText).toContain('Difficulty · Hard');
    expect(footerText).toContain('Updated 2025/1/1');

    mounted.unmount();
  });

  test('omits difficulty metadata when it is unspecified', async () => {
    const mounted = await mountDeckListCard('browse', { deck: { difficulty: null } });

    expect(mounted.container.querySelector('[data-testid="deck-difficulty"]')).toBeNull();

    mounted.unmount();
  });

  test('keeps owned deck cards on the management layout', async () => {
    const mounted = await mountDeckListCard('owned');
    const text = mounted.container.textContent ?? '';
    const footerText = mounted.container.querySelector('.deck-list-card-footer-meta')?.textContent ?? '';

    expect(mounted.container.querySelector('.deck-list-card-owned')).not.toBeNull();
    expect(mounted.container.querySelector('img[alt="Azure Hero"]')).not.toBeNull();
    expect(text).toContain('Azure Tempo');
    expect(text).toContain('Public');
    expect(text).toContain('{F}');
    expect(text).toContain('Damage');
    expect(text).toContain('Armor');
    expect(text).toContain('Tempo Burst');
    expect(mounted.container.querySelector('.deck-list-card-title-row')?.textContent).not.toContain('Damage');
    expect(mounted.container.querySelector('.deck-list-card-title-row')?.textContent).not.toContain('Tempo Burst');
    expect(mounted.container.querySelector('.deck-list-card-tags')?.textContent).toContain('Damage');
    expect(mounted.container.querySelector('.deck-list-card-tags')?.textContent).toContain('Tempo Burst');
    expect(text).not.toContain('Maindeck 40 · 24 unique · 1 sideboard');
    expect(footerText).not.toContain('Azure Hero');
    expect(footerText).toContain('Maindeck 40');
    expect(footerText).toContain('Unique 24');
    expect(footerText).toContain('Sideboards 1');
    expect(footerText).toContain('Updated 2025/1/1');

    mounted.unmount();
  });

  test('browse card keeps the expected navigation target', async () => {
    const mounted = await mountDeckListCard('browse');
    const card = mounted.container.querySelector('.deck-list-card-browse');

    expect(card).not.toBeNull();
    expect(card?.getAttribute('data-navigation-target')).toBe('/decks/deck-1');

    mounted.unmount();
  });

  test('renders custom actions in browse mode instead of the fallback actions menu', async () => {
    const mounted = await mountDeckListCard('browse', { customActions: true });

    expect(mounted.container.textContent).toContain('Custom Action');
    expect(mounted.container.querySelector('button[aria-label="Open deck actions"]')).toBeNull();

    mounted.unmount();
  });

  test('renders injected browse menu actions with the fallback actions', async () => {
    const mounted = await mountDeckListCard('browse', { menuActions: true });
    const menuTrigger = mounted.container.querySelector('button[aria-label="Open deck actions"]');

    menuTrigger?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await nextTick();

    expect(document.body.textContent).toContain('Tags');
    expect(document.body.textContent).toContain('Playtest');
    expect(document.body.textContent).toContain('Share');
    expect(document.body.textContent).toContain('TTS');
    expect(document.body.textContent).not.toContain('Copy Share Link');
    expect(document.body.textContent).not.toContain('Copy TTS');
    const sharedMenuActions = Array.from(document.body.querySelectorAll('.app-menu-action'));
    expect(sharedMenuActions).toHaveLength(3);
    expect(sharedMenuActions.every((action) => action.classList.contains('btn-secondary'))).toBe(true);
    expect(Array.from(document.body.querySelectorAll('.app-menu-action svg')).every((icon) =>
      icon.classList.contains('h-4') && icon.classList.contains('w-4'))).toBe(true);

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
    const copyShareButton = document.body.querySelector<HTMLButtonElement>('button[aria-label="Copy share link"]');

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

    const exportButton = document.body.querySelector<HTMLButtonElement>('button[aria-label="Copy Mainboard TTS"]');

    expect(exportButton).not.toBeNull();

    exportButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await nextTick();

    expect(exportTtsDeckMock).toHaveBeenCalledWith('deck-1');
    expect(mounted.router.currentRoute.value.fullPath).toBe('/decks');

    mounted.unmount();
  });
});

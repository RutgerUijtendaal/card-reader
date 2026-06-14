/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import PlaytesterPage from '@/modules/playtester/PlaytesterPage.vue';
import {
  createInitialPlaytestState,
  getZoneInstances,
  serializePlaytestDraft,
} from '@/modules/playtester/playtestState';

const {
  authState,
  fetchCurrentCardBackMock,
  fetchDeckDetailMock,
  fetchMyDeckMock,
} = vi.hoisted(() => ({
  authState: {
    authenticated: true,
  },
  fetchCurrentCardBackMock: vi.fn(),
  fetchDeckDetailMock: vi.fn(),
  fetchMyDeckMock: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/modules/auth/authStore', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/modules/decks/api', () => ({
  fetchDeckDetail: fetchDeckDetailMock,
  fetchMyDeck: fetchMyDeckMock,
}));

vi.mock('@/modules/playtester/api', () => ({
  fetchCurrentCardBack: fetchCurrentCardBackMock,
}));

vi.mock('@/components/app/AppPageHeader.vue', () => ({
  default: defineComponent({
    props: {
      title: { type: String, required: true },
    },
    setup(props, { slots }) {
      return () => h('header', [h('h1', props.title), slots.actions?.()]);
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

const card = {
  id: 'card-1',
  key: 'card-1',
  label: 'Card 1',
  result_type: 'card' as const,
  image_url: null,
  is_hero: false,
  lifecycle_status: 'active' as const,
  template_id: '',
  version_id: 'card-1-version',
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name: 'Card 1',
  type_line: '',
  mana_cost: '',
  mana_symbols: [],
  mana_value: 1,
  attack: null,
  health: null,
  rules_text: '',
  confidence: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

const manaCard = {
  ...card,
  id: 'mana-card',
  key: 'mana-card',
  label: 'Mana Card',
  name: 'Mana Card',
  version_id: 'mana-card-version',
  types: [{ id: 'mana', key: 'mana', label: 'Mana' }],
};

const setupCard = {
  ...card,
  id: 'setup-card',
  key: 'setup-card',
  label: 'Setup Card',
  name: 'Setup Card',
  version_id: 'setup-card-version',
  keywords: ['Setup'],
};

const deckRecord = {
  id: 'deck-1',
  name: 'Playtest Deck',
  description: null,
  visibility: 'public' as const,
  owner: { id: 'user-1', username: 'owner' },
  hero_card: { ...card, id: 'hero', key: 'hero', name: 'Hero', label: 'Hero', is_hero: true },
  mainboard: {
    total_cards: 10,
    unique_cards: 3,
    entries: [
      { quantity: 2, card: manaCard },
      { quantity: 1, card: setupCard },
      { quantity: 7, card },
    ],
  },
  sideboards: [],
  totals: {
    overall_total_cards: 10,
    overall_unique_cards: 3,
    mainboard_total_cards: 10,
    mainboard_unique_cards: 3,
  },
  status: {
    is_valid: true,
    label: 'Ready',
    issues: [],
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const flushPage = async (): Promise<void> => {
  await nextTick();
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
  await nextTick();
};

const mountPage = async (): Promise<{ container: HTMLElement; router: ReturnType<typeof createRouter>; unmount: () => void }> => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/playtester/:deckId', component: PlaytesterPage },
      { path: '/playtester', component: { template: '<div />' } },
      { path: '/decks/:id', component: { template: '<div />' } },
    ],
  });
  await router.push('/playtester/deck-1');
  await router.isReady();
  const app = createApp(PlaytesterPage);
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

const testZone = (container: HTMLElement, testId: string): HTMLElement => {
  const zone = container.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
  if (!zone) {
    throw new Error(`expected ${testId} zone`);
  }
  return zone;
};

const keepOpeningHand = async (container: HTMLElement): Promise<void> => {
  const keepButton = [...container.querySelectorAll<HTMLButtonElement>('button')]
    .find((button) => button.textContent?.includes('Keep this'));
  if (!keepButton) {
    throw new Error('expected keep button');
  }
  keepButton.click();
  await flushPage();
};

const playtestPointerEvent = (
  type: string,
  init: MouseEventInit & { pointerId?: number } = {},
): PointerEvent => {
  const event = new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    button: 0,
    ...init,
  }) as PointerEvent;
  Object.defineProperty(event, 'pointerId', { value: init.pointerId ?? 1 });
  return event;
};

const rect = (
  left: number,
  top: number,
  width: number,
  height: number,
): DOMRect => ({
  x: left,
  y: top,
  left,
  top,
  right: left + width,
  bottom: top + height,
  width,
  height,
  toJSON: () => ({}),
});

describe('PlaytesterPage', () => {
  beforeEach(() => {
    localStorage.clear();
    authState.authenticated = true;
    fetchMyDeckMock.mockRejectedValue(new Error('not owned'));
    fetchDeckDetailMock.mockResolvedValue(deckRecord);
    fetchCurrentCardBackMock.mockResolvedValue({
      current: {
        id: 'card-back-1',
        label: 'Current Back',
        width: 630,
        height: 880,
        image_url: '/card-images/back.webp',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    });
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  test('falls back to public deck detail when owned deck fetch fails', async () => {
    const mounted = await mountPage();

    expect(fetchMyDeckMock).toHaveBeenCalledWith('deck-1');
    expect(fetchDeckDetailMock).toHaveBeenCalledWith('deck-1');
    expect(mounted.container.textContent).toContain('Playtest Deck');
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).toContain('Opening hand');
    expect(mounted.container.querySelector('[data-testid="playtest-hero-zone"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="playtest-other-zone"]')).toBeNull();

    mounted.unmount();
  });

  test('reloads deck data when navigating between playtester deck routes', async () => {
    fetchDeckDetailMock.mockImplementation((deckId: string) =>
      Promise.resolve({
        ...deckRecord,
        id: deckId,
        name: deckId === 'deck-2' ? 'Second Playtest Deck' : 'Playtest Deck',
      }),
    );
    const mounted = await mountPage();

    expect(mounted.container.textContent).toContain('Playtest Deck');

    await mounted.router.push('/playtester/deck-2');
    await flushPage();

    expect(fetchDeckDetailMock).toHaveBeenCalledWith('deck-2');
    expect(mounted.container.textContent).toContain('Second Playtest Deck');
    expect(localStorage.getItem('card-reader.playtester.deck-2')).not.toBeNull();

    mounted.unmount();
  });

  test('requires stale draft choice before current deck controls are interactive', async () => {
    const staleState = {
      ...createInitialPlaytestState(deckRecord),
      deckUpdatedAt: '2025-01-01T00:00:00Z',
    };
    localStorage.setItem('card-reader.playtester.deck-1', JSON.stringify(serializePlaytestDraft(staleState)));

    const mounted = await mountPage();

    expect(mounted.container.textContent).toContain('Saved playtest is from an older deck version.');
    expect(mounted.container.querySelector('[data-testid="playtest-opening-setup"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="playtest-board-zone"]')).toBeNull();

    const restartButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Restart');
    restartButton?.click();
    await flushPage();

    expect(mounted.container.textContent).not.toContain('Saved playtest is from an older deck version.');
    expect(testZone(mounted.container, 'playtest-opening-setup')).not.toBeNull();
    expect(localStorage.getItem('card-reader.playtester.deck-1')).not.toBeNull();

    mounted.unmount();
  });

  test('opening setup shows physical mana and Setup selections before the board', async () => {
    const mounted = await mountPage();

    expect(testZone(mounted.container, 'playtest-opening-hand').querySelectorAll('[data-instance-id]')).toHaveLength(7);
    expect(testZone(mounted.container, 'playtest-opening-mana').querySelectorAll('.playtest-opening-card-choice')).toHaveLength(2);
    expect(testZone(mounted.container, 'playtest-opening-setup-cards').querySelectorAll('.playtest-opening-card-choice')).toHaveLength(1);
    expect(testZone(mounted.container, 'playtest-opening-hand').querySelector('.theme-section-title')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-mana').querySelector('.theme-section-title')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-setup-cards').querySelector('.theme-section-title')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-setup')
      .querySelectorAll('[data-instance-id][role="button"]')).toHaveLength(0);
    expect(testZone(mounted.container, 'playtest-opening-setup')
      .querySelectorAll('[data-instance-id][tabindex]')).toHaveLength(0);

    const manaChoice = testZone(mounted.container, 'playtest-opening-mana')
      .querySelector<HTMLButtonElement>('.playtest-opening-card-choice');
    manaChoice?.click();
    await flushPage();

    expect(manaChoice?.getAttribute('aria-pressed')).toBe('true');

    const mulliganButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Mulligan'));
    mulliganButton?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-opening-mana')
      .querySelector<HTMLButtonElement>('.playtest-opening-card-choice')?.getAttribute('aria-pressed')).toBe('true');

    await keepOpeningHand(mounted.container);

    expect(testZone(mounted.container, 'playtest-board-zone')).not.toBeNull();
    expect(mounted.container.querySelectorAll('[data-testid="playtest-board-card"] [data-instance-id]')).toHaveLength(1);

    mounted.unmount();
  });

  test('supports hand-to-play, tap, and next turn click defaults', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const toolbarButtons = [...mounted.container.querySelectorAll<HTMLButtonElement>('.playtester-topbar button')]
      .map((button) => button.textContent?.trim());
    expect(toolbarButtons).toContain('Next turn');
    expect(toolbarButtons).not.toContain('Draw');
    expect(toolbarButtons).not.toContain('Draw to Hand');

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    handCard?.click();
    await flushPage();
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(6);
    expect(mounted.container.querySelectorAll('[data-testid="playtest-board-card"] [data-instance-id]')).toHaveLength(1);

    const playCard = mounted.container.querySelector<HTMLElement>('[data-testid="playtest-board-card"] [data-instance-id]');
    playCard?.click();
    await flushPage();
    expect(playCard?.className).toContain('playtest-card-tapped');

    const nextTurnButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('.playtester-topbar button')]
      .find((button) => button.textContent?.includes('Next turn'));
    nextTurnButton?.click();
    await flushPage();

    const updatedPlayCard = mounted.container.querySelector<HTMLElement>('[data-testid="playtest-board-card"] [data-instance-id]');
    expect(updatedPlayCard?.className).not.toContain('playtest-card-tapped');
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(7);

    mounted.unmount();
  });

  test('middle-click hold zooms board cards until release or leave', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    handCard?.click();
    await flushPage();

    const playCard = mounted.container.querySelector<HTMLElement>('[data-testid="playtest-board-card"] [data-instance-id]');
    vi.stubGlobal('innerWidth', 800);
    vi.stubGlobal('innerHeight', 600);
    if (playCard) {
      vi.spyOn(playCard, 'getBoundingClientRect').mockReturnValue(rect(760, 500, 100, 140));
    }
    playCard?.dispatchEvent(playtestPointerEvent('pointerdown', { button: 1, clientX: 40, clientY: 40 }));
    await flushPage();

    expect(playCard?.className).toContain('playtest-card-middle-zoom');
    const overlay = document.body.querySelector<HTMLElement>('[data-testid="playtest-card-zoom-overlay"]');
    expect(overlay).not.toBeNull();
    expect(Number.parseFloat(overlay?.style.left ?? '')).toBeCloseTo(476);
    expect(Number.parseFloat(overlay?.style.top ?? '')).toBeCloseTo(151.2);
    expect(Number.parseFloat(overlay?.style.width ?? '')).toBeCloseTo(312);
    expect(Number.parseFloat(overlay?.style.height ?? '')).toBeCloseTo(436.8);

    playCard?.dispatchEvent(playtestPointerEvent('pointerleave', { button: 1, clientX: 160, clientY: 160 }));
    await flushPage();

    expect(playCard?.className).not.toContain('playtest-card-middle-zoom');
    expect(document.body.querySelector('[data-testid="playtest-card-zoom-overlay"]')).toBeNull();

    mounted.unmount();
  });

  test('middle-click zoom uses a readable fixed size for compact rotated hand cards', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    vi.stubGlobal('innerWidth', 800);
    vi.stubGlobal('innerHeight', 600);
    if (handCard) {
      vi.spyOn(handCard, 'getBoundingClientRect').mockReturnValue(rect(320, 500, 240, 340));
      Object.defineProperties(handCard, {
        offsetHeight: { configurable: true, value: 84 },
        offsetWidth: { configurable: true, value: 60 },
      });
    }
    handCard?.dispatchEvent(playtestPointerEvent('pointerdown', { button: 1, clientX: 360, clientY: 540 }));
    await flushPage();

    const overlay = document.body.querySelector<HTMLElement>('[data-testid="playtest-card-zoom-overlay"]');
    expect(overlay).not.toBeNull();
    expect(Number.parseFloat(overlay?.style.left ?? '')).toBeCloseTo(284);
    expect(Number.parseFloat(overlay?.style.top ?? '')).toBeCloseTo(151.2);
    expect(Number.parseFloat(overlay?.style.width ?? '')).toBeCloseTo(312);
    expect(Number.parseFloat(overlay?.style.height ?? '')).toBeCloseTo(436.8);

    handCard?.dispatchEvent(playtestPointerEvent('pointerleave', { button: 1, clientX: 360, clientY: 540 }));
    await flushPage();

    expect(document.body.querySelector('[data-testid="playtest-card-zoom-overlay"]')).toBeNull();

    mounted.unmount();
  });

  test('renders a first-class dragged card overlay during pointer drag', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    handCard?.dispatchEvent(playtestPointerEvent('pointerdown', { clientX: 10, clientY: 10 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { clientX: 34, clientY: 34 }));
    await flushPage();

    expect(document.body.querySelector('[data-testid="playtest-dragged-card"]')).not.toBeNull();

    window.dispatchEvent(playtestPointerEvent('pointerup', { clientX: 34, clientY: 34 }));
    await flushPage();

    expect(document.body.querySelector('[data-testid="playtest-dragged-card"]')).toBeNull();

    mounted.unmount();
  });

  test('pointercancel aborts active drags without moving cards', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    const handZone = testZone(mounted.container, 'playtest-hand-zone');
    const handCard = handZone.querySelector<HTMLElement>('[data-instance-id]');
    if (!handCard) {
      throw new Error('expected hand card');
    }
    vi.spyOn(handCard, 'getBoundingClientRect').mockReturnValue(rect(90, 90, 100, 140));
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 500, 400));

    handCard.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 9, clientX: 100, clientY: 100 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 9, clientX: 130, clientY: 130 }));
    await flushPage();

    expect(document.body.querySelector('[data-testid="playtest-dragged-card"]')).not.toBeNull();

    window.dispatchEvent(playtestPointerEvent('pointercancel', { pointerId: 9, clientX: 250, clientY: 180 }));
    await flushPage();

    expect(document.body.querySelector('[data-testid="playtest-dragged-card"]')).toBeNull();
    expect(handZone.querySelectorAll('[data-instance-id]')).toHaveLength(7);
    expect(board.querySelectorAll('[data-instance-id][data-playtest-zone-id="play"]')).toHaveLength(0);

    mounted.unmount();
  });

  test('drops short drags through the source card onto the board underneath', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    if (!handCard) {
      throw new Error('expected hand card');
    }
    vi.spyOn(handCard, 'getBoundingClientRect').mockReturnValue(rect(90, 90, 100, 140));
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      right: 500,
      bottom: 400,
      width: 500,
      height: 400,
      toJSON: () => ({}),
    });
    const originalElementsFromPoint = document.elementsFromPoint;
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [handCard, board],
    });

    handCard.dispatchEvent(playtestPointerEvent('pointerdown', { clientX: 100, clientY: 100 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { clientX: 103, clientY: 103 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { clientX: 110, clientY: 110 }));
    await flushPage();

    expect(mounted.container.querySelectorAll('[data-testid="playtest-board-card"] [data-instance-id]')).toHaveLength(1);
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(6);
    const boardCard = mounted.container.querySelector<HTMLElement>('[data-testid="playtest-board-card"]');
    expect(boardCard?.style.left).toBe('30%');
    expect(boardCard?.style.top).toBe('42.5%');

    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: originalElementsFromPoint,
    });
    mounted.unmount();
  });

  test('selects board cards with a drag box and drags the selection as a group', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 500, 400));

    const firstHandCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    firstHandCard?.click();
    await flushPage();
    const secondHandCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    secondHandCard?.click();
    await flushPage();

    const boardCards = [...board.querySelectorAll<HTMLElement>('[data-instance-id][data-playtest-zone-id="play"]')];
    expect(boardCards).toHaveLength(2);
    vi.spyOn(boardCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(60, 60, 100, 140));
    vi.spyOn(boardCards[1] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(220, 60, 100, 140));

    board.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 2, clientX: 40, clientY: 40 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 2, clientX: 340, clientY: 240 }));
    await nextTick();
    expect(mounted.container.querySelector('[data-testid="playtest-selection-box"]')).not.toBeNull();
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 2, clientX: 340, clientY: 240 }));
    await flushPage();

    const table = mounted.container.querySelector<HTMLElement>('.playtester-table');
    expect(table?.dataset.playtestSelectedCount).toBe('2');
    expect(boardCards.every((element) => element.className.includes('playtest-card-selected'))).toBe(true);
    expect(board.querySelectorAll('[data-playtest-selected="true"]')).toHaveLength(2);

    boardCards[0]?.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 3, clientX: 100, clientY: 100 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 3, clientX: 150, clientY: 100 }));
    await flushPage();

    expect(document.body.querySelectorAll('[data-testid="playtest-dragged-card"]')).toHaveLength(2);

    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 3, clientX: 150, clientY: 100 }));
    await flushPage();

    const boardWrappers = [...mounted.container.querySelectorAll<HTMLElement>('[data-testid="playtest-board-card"]')];
    expect(boardWrappers.map((element) => element.style.left)).toEqual(['26%', '42%']);
    expect(boardWrappers.map((element) => element.style.top)).toEqual(['22%', '22%']);

    mounted.unmount();
  });

  test('ignores selected board group drops outside board and drop targets', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 500, 400));

    const firstHandCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    firstHandCard?.click();
    await flushPage();
    const secondHandCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    secondHandCard?.click();
    await flushPage();

    const boardCards = [...board.querySelectorAll<HTMLElement>('[data-instance-id][data-playtest-zone-id="play"]')];
    expect(boardCards).toHaveLength(2);
    vi.spyOn(boardCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(60, 60, 100, 140));
    vi.spyOn(boardCards[1] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(220, 60, 100, 140));

    board.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 11, clientX: 40, clientY: 40 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 11, clientX: 340, clientY: 240 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 11, clientX: 340, clientY: 240 }));
    await flushPage();

    const boardWrappersBefore = [...mounted.container.querySelectorAll<HTMLElement>('[data-testid="playtest-board-card"]')];
    const positionsBefore = boardWrappersBefore.map((element) => [element.style.left, element.style.top]);
    const originalElementsFromPoint = document.elementsFromPoint;
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [],
    });

    boardCards[0]?.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 12, clientX: 100, clientY: 100 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 12, clientX: 650, clientY: 100 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 12, clientX: 650, clientY: 100 }));
    await flushPage();

    const boardWrappersAfter = [...mounted.container.querySelectorAll<HTMLElement>('[data-testid="playtest-board-card"]')];
    expect(boardWrappersAfter.map((element) => [element.style.left, element.style.top])).toEqual(positionsBefore);

    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: originalElementsFromPoint,
    });
    mounted.unmount();
  });

  test('dropping a pulled stack card back on the same stack preserves stack order', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const libraryZone = testZone(mounted.container, 'playtest-library-zone');
    const stackCard = libraryZone.querySelector<HTMLElement>('.playtest-stack-card');
    if (!stackCard) {
      throw new Error('expected library stack card');
    }
    vi.spyOn(libraryZone, 'getBoundingClientRect').mockReturnValue(rect(300, 300, 120, 180));
    vi.spyOn(stackCard, 'getBoundingClientRect').mockReturnValue(rect(310, 330, 100, 140));
    const originalElementsFromPoint = document.elementsFromPoint;
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [libraryZone],
    });
    const draftBefore = JSON.parse(localStorage.getItem('card-reader.playtester.deck-1') ?? '{}');
    const libraryBefore = getZoneInstances(draftBefore.state, 'library').map((instance) => instance.instanceId);

    libraryZone.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 10, clientX: 320, clientY: 340 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 10, clientX: 340, clientY: 360 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 10, clientX: 340, clientY: 360 }));
    await flushPage();

    const draftAfter = JSON.parse(localStorage.getItem('card-reader.playtester.deck-1') ?? '{}');
    const libraryAfter = getZoneInstances(draftAfter.state, 'library').map((instance) => instance.instanceId);
    expect(libraryAfter).toEqual(libraryBefore);

    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: originalElementsFromPoint,
    });
    mounted.unmount();
  });

  test('moves selected board card groups into hand and stack zones', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 500, 400));

    const moveFourHandCardsToBoard = async (): Promise<HTMLElement[]> => {
      for (let count = 0; count < 4; count += 1) {
        testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
        await flushPage();
      }
      const boardCards = [...board.querySelectorAll<HTMLElement>('[data-instance-id][data-playtest-zone-id="play"]')];
      expect(boardCards).toHaveLength(4);
      return boardCards;
    };

    const mockSelectedPairBounds = (boardCards: HTMLElement[]): void => {
      vi.spyOn(boardCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(60, 60, 100, 140));
      vi.spyOn(boardCards[1] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(220, 60, 100, 140));
      boardCards.slice(2).forEach((card, index) => {
        vi.spyOn(card, 'getBoundingClientRect').mockReturnValue(rect(60 + index * 160, 320, 100, 140));
      });
    };

    const selectBoardCards = async (): Promise<void> => {
      board.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 4, clientX: 40, clientY: 40 }));
      window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 4, clientX: 340, clientY: 240 }));
      window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 4, clientX: 340, clientY: 240 }));
      await flushPage();
      expect(mounted.container.querySelector<HTMLElement>('.playtester-table')?.dataset.playtestSelectedCount).toBe('2');
    };

    let boardCards = await moveFourHandCardsToBoard();
    mockSelectedPairBounds(boardCards);
    await selectBoardCards();

    const originalElementsFromPoint = document.elementsFromPoint;
    const handZone = testZone(mounted.container, 'playtest-hand-zone');
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [handZone],
    });

    boardCards[0]?.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 5, clientX: 100, clientY: 100 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 5, clientX: 160, clientY: 360 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 5, clientX: 160, clientY: 360 }));
    await flushPage();

    expect(board.querySelectorAll('[data-instance-id][data-playtest-zone-id="play"]')).toHaveLength(2);
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(5);

    boardCards = [...board.querySelectorAll<HTMLElement>('[data-instance-id][data-playtest-zone-id="play"]')];
    mockSelectedPairBounds(boardCards);
    await selectBoardCards();

    const discardZone = testZone(mounted.container, 'playtest-discard-zone');
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [discardZone],
    });

    boardCards[0]?.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 6, clientX: 100, clientY: 100 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 6, clientX: 420, clientY: 360 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 6, clientX: 420, clientY: 360 }));
    await flushPage();

    expect(board.querySelectorAll('[data-instance-id][data-playtest-zone-id="play"]')).toHaveLength(0);
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(5);
    expect(testZone(mounted.container, 'playtest-discard-zone').textContent).toContain('2');

    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: originalElementsFromPoint,
    });
    mounted.unmount();
  });

  test('opens right-click context menus for cards and stacks', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const stackContext = new MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 20, clientY: 20 });
    testZone(mounted.container, 'playtest-hero-zone').dispatchEvent(stackContext);
    await flushPage();

    expect(stackContext.defaultPrevented).toBe(true);
    const stackMenuText = document.body.querySelector('[data-testid="playtest-context-menu"]')?.textContent ?? '';
    expect(stackMenuText).toContain('Open Stack');
    expect(stackMenuText.match(/Open Stack/g)).toHaveLength(1);

    const libraryContext = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
      clientX: 24,
      clientY: 24,
    });
    testZone(mounted.container, 'playtest-library-zone').dispatchEvent(libraryContext);
    await flushPage();

    const libraryMenuText = document.body.querySelector('[data-testid="playtest-context-menu"]')?.textContent ?? '';
    expect(libraryMenuText).toContain('Draw Top Card');
    expect(libraryMenuText.match(/Open Stack/g)).toHaveLength(1);

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    const cardContext = new MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 40, clientY: 40 });
    handCard?.dispatchEvent(cardContext);
    await flushPage();

    expect(cardContext.defaultPrevented).toBe(true);
    expect(document.body.querySelector('[data-testid="playtest-context-menu"]')?.textContent).toContain('Move to Board');

    mounted.unmount();
  });

  test('tracks hovered entity actions for future hotkeys', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const table = mounted.container.querySelector<HTMLElement>('.playtester-table');
    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    handCard?.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    await flushPage();

    expect(Number(table?.dataset.playtestHoverActions)).toBeGreaterThan(0);

    handCard?.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
    await flushPage();

    expect(Number(table?.dataset.playtestHoverActions)).toBe(0);

    mounted.unmount();
  });
});

/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import PlaytesterPage from '@/modules/playtester/PlaytesterPage.vue';
import {
  createInitialPlaytestState,
  getZoneInstances,
  moveInstanceToZone,
  serializePlaytestDraft,
} from '@/modules/playtester/playtestState';

const {
  authState,
  fetchCurrentCardBackMock,
  fetchDeckDetailMock,
  fetchMyDeckMock,
  fetchMyDeckSummariesMock,
  fetchPublicDeckSummariesMock,
} = vi.hoisted(() => ({
  authState: {
    authenticated: true,
  },
  fetchCurrentCardBackMock: vi.fn(),
  fetchDeckDetailMock: vi.fn(),
  fetchMyDeckMock: vi.fn(),
  fetchMyDeckSummariesMock: vi.fn(),
  fetchPublicDeckSummariesMock: vi.fn(),
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
  fetchMyDeckSummaries: fetchMyDeckSummariesMock,
  fetchPublicDeckSummaries: fetchPublicDeckSummariesMock,
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
    total_cards: 14,
    unique_cards: 3,
    entries: [
      { quantity: 3, card: manaCard },
      { quantity: 1, card: setupCard },
      { quantity: 10, card },
    ],
  },
  sideboards: [],
  totals: {
    overall_total_cards: 14,
    overall_unique_cards: 3,
    mainboard_total_cards: 14,
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

const deckRecordWithoutSetupCards = () => ({
  ...deckRecord,
  mainboard: {
    ...deckRecord.mainboard,
    total_cards: 13,
    unique_cards: 2,
    entries: deckRecord.mainboard.entries.filter((entry) => entry.card.id !== setupCard.id),
  },
  totals: {
    ...deckRecord.totals,
    overall_total_cards: 13,
    overall_unique_cards: 2,
    mainboard_total_cards: 13,
    mainboard_unique_cards: 2,
  },
});

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
      { path: '/playtester', component: PlaytesterPage },
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

const nonSetupBoardCards = (board: HTMLElement): HTMLElement[] =>
  [...board.querySelectorAll<HTMLElement>(
    '[data-instance-id][data-playtest-zone-id="play"]:not([data-playtest-setup-origin="true"])',
  )];

const nonSetupBoardWrappers = (board: HTMLElement): HTMLElement[] =>
  nonSetupBoardCards(board)
    .map((card) => card.closest<HTMLElement>('[data-testid="playtest-board-card"]'))
    .filter((card): card is HTMLElement => card !== null);

const keepOpeningHand = async (container: HTMLElement): Promise<void> => {
  if (container.querySelector('[data-testid="playtest-opening-mana"]')) {
    const manaButtons = [...container.querySelectorAll<HTMLButtonElement>('.playtest-opening-copy-button')];
    for (const button of manaButtons.slice(0, 3)) {
      button.click();
      await flushPage();
    }
    const nextButton = container.querySelector<HTMLButtonElement>('button[aria-label="Next step"]');
    if (!nextButton) {
      throw new Error('expected opening mana next button');
    }
    nextButton.click();
    await flushPage();
  }
  if (
    container.querySelector('[data-testid="playtest-opening-setup-cards"]')
    || container.querySelector('[data-testid="playtest-opening-library-browser"]')
  ) {
    const drawHandButton = container.querySelector<HTMLButtonElement>('button[aria-label="Next step"]');
    if (!drawHandButton) {
      throw new Error('expected setup draw hand button');
    }
    drawHandButton.click();
    await flushPage();
  }
  const keepButton = [...container.querySelectorAll<HTMLButtonElement>('button')]
    .find((button) => button.textContent?.includes('Keep this'));
  if (!keepButton) {
    throw new Error('expected keep button');
  }
  keepButton.click();
  await flushPage();
};

const createPlaytestDraftWithDiscardStack = (): void => {
  let state = createInitialPlaytestState(deckRecord, () => 0);
  for (const instance of getZoneInstances(state, 'library').slice(0, 2)) {
    state = moveInstanceToZone(state, instance.instanceId, 'discard');
  }
  localStorage.setItem('card-reader.playtester.deck-1', JSON.stringify(serializePlaytestDraft({
    ...state,
    phase: 'play',
  })));
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

const playtestKeyEvent = (
  key: string,
  init: KeyboardEventInit = {},
): KeyboardEvent => new KeyboardEvent('keydown', {
  bubbles: true,
  cancelable: true,
  key,
  ...init,
});

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
    fetchMyDeckSummariesMock.mockResolvedValue([]);
    fetchPublicDeckSummariesMock.mockResolvedValue([]);
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
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).toContain('Starting mana');
    expect(testZone(mounted.container, 'playtest-hero-zone')).not.toBeNull();
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

  test('returns to pre-setup without clearing the saved draft', async () => {
    const mounted = await mountPage();

    expect(mounted.container.textContent).toContain('Playtest Deck');
    expect(localStorage.getItem('card-reader.playtester.deck-1')).not.toBeNull();

    await mounted.router.push('/playtester');
    await flushPage();

    expect(mounted.container.querySelector('[data-testid="playtester-pre-setup-surface"]')).not.toBeNull();
    expect(mounted.container.textContent).toContain('Select Deck');
    expect(localStorage.getItem('card-reader.playtester.deck-1')).not.toBeNull();

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

  test('updates stored playtester card scale from Alt wheel during opening setup', async () => {
    const mounted = await mountPage();
    const surface = mounted.container.querySelector<HTMLElement>('.playtester-table');
    if (!surface) {
      throw new Error('expected playtester table');
    }

    surface.dispatchEvent(new WheelEvent('wheel', {
      altKey: true,
      bubbles: true,
      cancelable: true,
      deltaY: -100,
    }));
    await flushPage();

    expect(surface.getAttribute('style')).toContain('--playtest-card-width: 7.80rem');
    expect(localStorage.getItem('card-reader.playtester.card-scale')).toBe('0.8');

    const scaleInput = testZone(mounted.container, 'playtest-opening-setup')
      .querySelector<HTMLInputElement>('.playtester-scale');
    if (!scaleInput) {
      throw new Error('expected opening setup scale input');
    }
    scaleInput.value = '1.05';
    scaleInput.dispatchEvent(new Event('input', { bubbles: true }));
    await flushPage();

    expect(surface.getAttribute('style')).toContain('--playtest-card-width: 10.24rem');
    expect(localStorage.getItem('card-reader.playtester.card-scale')).toBe('1.05');

    mounted.unmount();
  });

  test('opening setup guides mana, setup actions, then hand before the board', async () => {
    const mounted = await mountPage();

    expect(testZone(mounted.container, 'playtest-opening-mana')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="playtest-opening-hand"]')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).toContain('Mana');
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).toContain('Setup');
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).toContain('Hand');
    expect(testZone(mounted.container, 'playtest-opening-mana').querySelectorAll('.playtest-opening-copy-button')).toHaveLength(3);
    expect(testZone(mounted.container, 'playtest-library-zone')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-discard-zone')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-banish-zone')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-hero-zone')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-library-zone').classList.contains('playtest-stack-collapsed')).toBe(false);
    expect(testZone(mounted.container, 'playtest-discard-zone').classList.contains('playtest-stack-collapsed')).toBe(false);
    expect(testZone(mounted.container, 'playtest-banish-zone').classList.contains('playtest-stack-collapsed')).toBe(false);
    expect(testZone(mounted.container, 'playtest-hero-zone').classList.contains('playtest-stack-collapsed')).toBe(false);
    expect(testZone(mounted.container, 'playtest-opening-mana').querySelector('.theme-section-title')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-setup')
      .querySelectorAll('[data-instance-id][role="button"]')).toHaveLength(0);
    expect(testZone(mounted.container, 'playtest-opening-setup')
      .querySelectorAll('[data-instance-id][tabindex]')).toHaveLength(0);
    expect(testZone(mounted.container, 'playtest-opening-mana')
      .querySelector('.playtest-card-static')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-library-zone').className).toContain('playtest-stack-passive');
    expect([...testZone(mounted.container, 'playtest-opening-mana').querySelectorAll<HTMLButtonElement>('button')]
      .some((button) => button.textContent?.trim() === 'Setup board')).toBe(true);
    expect([...testZone(mounted.container, 'playtest-opening-mana').querySelectorAll<HTMLButtonElement>('button')]
      .some((button) => button.textContent?.trim() === 'Draw hand')).toBe(false);

    testZone(mounted.container, 'playtest-library-zone').click();
    await flushPage();

    expect(document.body.querySelector('[data-testid="playtest-stack-overlay"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="playtest-opening-hand"]')).toBeNull();

    const nextStepButton = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Next step"]');
    expect(nextStepButton?.disabled).toBe(true);
    expect(testZone(mounted.container, 'playtest-opening-picked-mana')
      .querySelectorAll('[data-instance-id]')).toHaveLength(0);
    const manaGroup = testZone(mounted.container, 'playtest-opening-mana')
      .querySelector<HTMLElement>('.playtest-opening-mana-card');
    manaGroup?.click();
    await flushPage();
    expect(testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll('.playtest-opening-copy-button-selected')).toHaveLength(1);
    manaGroup?.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }));
    await flushPage();
    expect(testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll('.playtest-opening-copy-button-selected')).toHaveLength(0);
    const manaChoices = [...testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll<HTMLButtonElement>('.playtest-opening-copy-button')];
    manaChoices[0]?.click();
    await flushPage();
    expect(manaChoices[0]?.getAttribute('aria-pressed')).toBe('true');
    expect(nextStepButton?.disabled).toBe(true);
    manaChoices[1]?.click();
    await flushPage();
    manaChoices[2]?.click();
    await flushPage();
    expect(testZone(mounted.container, 'playtest-opening-picked-mana')
      .querySelectorAll('[data-instance-id]')).toHaveLength(3);
    const acceptButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Setup board');
    expect(acceptButton?.disabled).toBe(false);
    expect(nextStepButton?.disabled).toBe(false);
    acceptButton?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-opening-setup-cards').textContent).toContain('Setup instructions');
    const manaStepButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('.playtest-opening-step')]
      .find((button) => button.textContent?.includes('Mana'));
    expect(manaStepButton?.disabled).toBe(false);
    manaStepButton?.click();
    await flushPage();
    expect(testZone(mounted.container, 'playtest-opening-mana')).not.toBeNull();
    const returnedManaAcceptButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Setup board');
    expect(returnedManaAcceptButton?.disabled).toBe(false);
    returnedManaAcceptButton?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-opening-setup-cards').textContent).toContain('Setup instructions');
    expect(testZone(mounted.container, 'playtest-library-zone')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-library-zone').className).toContain('playtest-stack-passive');
    testZone(mounted.container, 'playtest-library-zone').click();
    await flushPage();
    expect(document.body.querySelector('[data-testid="playtest-stack-overlay"]')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-setup-cards').textContent).toContain('Setup Card');
    const setupInstruction = testZone(mounted.container, 'playtest-opening-setup-cards')
      .querySelector<HTMLElement>('.playtest-opening-setup-card');
    const handledCheckbox = testZone(mounted.container, 'playtest-opening-setup-cards')
      .querySelector<HTMLInputElement>('input[type="checkbox"]');
    expect(handledCheckbox?.checked).toBe(false);
    setupInstruction?.click();
    await flushPage();
    expect(testZone(mounted.container, 'playtest-opening-setup-cards')
      .querySelector<HTMLInputElement>('input[type="checkbox"]')?.checked).toBe(true);
    expect([...testZone(mounted.container, 'playtest-opening-setup-cards').querySelectorAll<HTMLButtonElement>('button')]
      .some((button) => button.textContent?.includes('Draw hand'))).toBe(true);
    expect(testZone(mounted.container, 'playtest-opening-library-browser')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-library-browser').textContent).toContain('Library');
    expect([...testZone(mounted.container, 'playtest-opening-library-browser')
      .querySelectorAll<HTMLButtonElement>('button')]
      .some((button) => button.textContent?.includes('Hand'))).toBe(false);
    const playButton = [...testZone(mounted.container, 'playtest-opening-library-browser')
      .querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Play'));
    playButton?.click();
    await flushPage();
    expect(mounted.container.querySelector('[data-testid="playtest-opening-setup-play-zone"]')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-picked-mana')
      .querySelectorAll('[data-instance-id]')).toHaveLength(4);
    expect(testZone(mounted.container, 'playtest-opening-picked-mana').textContent).toContain('Play 1');
    const banishButton = [...testZone(mounted.container, 'playtest-opening-library-browser')
      .querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Banish'));
    banishButton?.click();
    await flushPage();
    expect(testZone(mounted.container, 'playtest-banish-zone').textContent).toContain('1');

    const drawHandButton = [...testZone(mounted.container, 'playtest-opening-setup-cards').querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Draw hand'));
    drawHandButton?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-opening-hand').querySelectorAll('[data-instance-id]')).toHaveLength(7);
    const handSizeInput = testZone(mounted.container, 'playtest-opening-setup')
      .querySelector<HTMLInputElement>('input[type="number"]');
    if (!handSizeInput) {
      throw new Error('expected hand size input');
    }
    handSizeInput.value = '';
    handSizeInput.dispatchEvent(new Event('input', { bubbles: true }));
    await flushPage();
    expect(testZone(mounted.container, 'playtest-opening-hand').querySelectorAll('[data-instance-id]')).toHaveLength(7);
    const mulliganButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Mulligan'));
    expect(mulliganButton?.textContent).toContain('[0]');
    mulliganButton?.click();
    await flushPage();

    expect([...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Mulligan'))?.textContent).toContain('[1]');
    expect(testZone(mounted.container, 'playtest-opening-hand').querySelectorAll('[data-instance-id]')).toHaveLength(7);

    await keepOpeningHand(mounted.container);

    expect(testZone(mounted.container, 'playtest-board-zone')).not.toBeNull();
    expect(mounted.container.querySelectorAll('[data-testid="playtest-board-card"] [data-instance-id]')).toHaveLength(4);
    expect(testZone(mounted.container, 'playtest-banish-zone').textContent).toContain('1');

    mounted.unmount();
  });

  test('can draw an opening hand directly after choosing starting mana', async () => {
    fetchDeckDetailMock.mockResolvedValueOnce(deckRecordWithoutSetupCards());
    const mounted = await mountPage();

    const drawHandButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Draw hand');
    const setupBoardButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Setup board');
    expect(drawHandButton?.disabled).toBe(true);
    expect(setupBoardButton?.disabled).toBe(true);

    const manaChoices = [...testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll<HTMLButtonElement>('.playtest-opening-copy-button')];
    for (const button of manaChoices.slice(0, 3)) {
      button.click();
      await flushPage();
    }

    expect(drawHandButton?.disabled).toBe(false);
    expect(setupBoardButton?.disabled).toBe(false);
    drawHandButton?.click();
    await flushPage();

    expect(mounted.container.querySelector('[data-testid="playtest-opening-setup-cards"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="playtest-opening-library-browser"]')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-hand').querySelectorAll('[data-instance-id]')).toHaveLength(7);
    expect(testZone(mounted.container, 'playtest-opening-picked-mana')
      .querySelectorAll('[data-instance-id]')).toHaveLength(3);

    mounted.unmount();
  });

  test('setup library cards can be dragged between setup zones without using the board', async () => {
    const mounted = await mountPage();

    const manaChoices = [...testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll<HTMLButtonElement>('.playtest-opening-copy-button')];
    for (const button of manaChoices.slice(0, 3)) {
      button.click();
      await flushPage();
    }
    const acceptButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Setup board');
    acceptButton?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-library-zone')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-library-zone').className).toContain('playtest-stack-passive');
    const libraryBrowser = testZone(mounted.container, 'playtest-opening-library-browser');
    const libraryCard = libraryBrowser.querySelector<HTMLElement>('[data-instance-id]');
    const handDropZone = testZone(mounted.container, 'playtest-opening-picked-mana');
    if (!libraryCard) {
      throw new Error('expected setup library card');
    }
    const libraryCardRect = vi.spyOn(libraryCard, 'getBoundingClientRect');
    libraryCardRect.mockReturnValue(rect(40, 120, 100, 140));

    const originalElementsFromPoint = document.elementsFromPoint;
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [handDropZone],
    });

    libraryCard.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 41, clientX: 50, clientY: 130 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 41, clientX: 90, clientY: 170 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 41, clientX: 90, clientY: 170 }));
    await flushPage();

    expect(handDropZone.textContent).not.toContain('Hand 1');
    const banishZone = testZone(mounted.container, 'playtest-banish-zone');
    libraryCardRect.mockReturnValue(rect(80, 420, 100, 140));
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [banishZone],
    });

    libraryCard.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 42, clientX: 90, clientY: 430 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 42, clientX: 180, clientY: 430 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 42, clientX: 180, clientY: 430 }));
    await flushPage();

    expect(testZone(mounted.container, 'playtest-banish-zone').textContent).toContain('1');
    const playButton = [...libraryBrowser.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Play'));
    playButton?.click();
    await flushPage();

    expect(handDropZone.textContent).toContain('Play 1');
    const stagedPlayCard = handDropZone.querySelector<HTMLElement>(
      '[data-playtest-zone-id="other"][data-playtest-setup-origin="true"]',
    );
    if (!stagedPlayCard) {
      throw new Error('expected staged play card');
    }
    vi.spyOn(stagedPlayCard, 'getBoundingClientRect').mockReturnValue(rect(120, 420, 100, 140));
    const discardZone = testZone(mounted.container, 'playtest-discard-zone');
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [discardZone],
    });

    stagedPlayCard.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 43, clientX: 130, clientY: 430 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 43, clientX: 210, clientY: 430 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 43, clientX: 210, clientY: 430 }));
    await flushPage();

    expect(handDropZone.textContent).not.toContain('Play 1');
    expect(testZone(mounted.container, 'playtest-discard-zone').textContent).toContain('1');
    expect(mounted.container.querySelectorAll('[data-testid="playtest-board-card"] [data-instance-id]')).toHaveLength(0);

    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: originalElementsFromPoint,
    });
    mounted.unmount();
  });

  test('centers the setup library when the deck has no Setup cards', async () => {
    fetchDeckDetailMock.mockResolvedValueOnce(deckRecordWithoutSetupCards());
    const mounted = await mountPage();

    expect(testZone(mounted.container, 'playtest-opening-mana')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).toContain('Mana');
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).toContain('Setup');
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).toContain('Hand');

    const manaChoices = [...testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll<HTMLButtonElement>('.playtest-opening-copy-button')];
    for (const button of manaChoices.slice(0, 3)) {
      button.click();
      await flushPage();
    }
    const acceptButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Setup board');
    acceptButton?.click();
    await flushPage();

    expect(mounted.container.querySelector('[data-testid="playtest-opening-setup-cards"]')).toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-setup').textContent).not.toContain('No cards with Setup tags found.');
    expect(testZone(mounted.container, 'playtest-opening-setup').querySelector('.playtest-opening-setup-stage-library-only')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-library-browser')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-opening-library-browser')
      .querySelector('.playtest-stack-browser-footer button')?.textContent).toContain('Draw hand');

    mounted.unmount();
  });

  test('keeps opening stack zone changes after accepting the hand', async () => {
    const mounted = await mountPage();

    const manaChoices = [...testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll<HTMLButtonElement>('.playtest-opening-copy-button')];
    for (const button of manaChoices.slice(0, 3)) {
      button.click();
      await flushPage();
    }
    const acceptButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Setup board');
    acceptButton?.click();
    await flushPage();

    const heroContext = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
      clientX: 10,
      clientY: 10,
    });
    testZone(mounted.container, 'playtest-hero-zone').dispatchEvent(heroContext);
    await flushPage();

    const openingHeroMenuText = document.body.querySelector('[data-testid="playtest-context-menu"]')?.textContent ?? '';
    expect(openingHeroMenuText).toContain('Open');
    expect(openingHeroMenuText).not.toContain('Top to Hand');
    expect(openingHeroMenuText).not.toContain('Top to Discard');
    expect(openingHeroMenuText).not.toContain('Top to Banish');
    expect(openingHeroMenuText).not.toContain('Top to Library');

    const libraryCard = testZone(mounted.container, 'playtest-opening-library-browser')
      .querySelector<HTMLElement>('[data-instance-id]');
    const libraryContext = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
      clientX: 20,
      clientY: 20,
    });
    libraryCard?.dispatchEvent(libraryContext);
    await flushPage();

    const openingLibraryMenuText = document.body.querySelector('[data-testid="playtest-context-menu"]')?.textContent ?? '';
    expect(openingLibraryMenuText).not.toContain('To Hand');
    expect(openingLibraryMenuText).toContain('To Discard');
    expect(openingLibraryMenuText).toContain('To Banish');
    expect(openingLibraryMenuText).toContain('To Hero');
    expect(openingLibraryMenuText).not.toContain('Draw');
    expect(openingLibraryMenuText).not.toContain('Shuffle');
    expect(openingLibraryMenuText).not.toContain('To Board');

    const topToDiscard = [...document.body.querySelectorAll<HTMLButtonElement>('[data-testid="playtest-context-menu"] button')]
      .find((button) => button.textContent?.includes('To Discard'));
    topToDiscard?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-discard-zone').textContent).toContain('1');

    await keepOpeningHand(mounted.container);

    expect(testZone(mounted.container, 'playtest-discard-zone').textContent).toContain('1');
    expect(mounted.container.querySelector<HTMLButtonElement>('[data-testid="playtest-undo"]')?.disabled).toBe(true);

    window.dispatchEvent(playtestKeyEvent('z', { ctrlKey: true }));
    await flushPage();

    expect(mounted.container.querySelector('[data-testid="playtest-opening-setup"]')).toBeNull();
    expect(testZone(mounted.container, 'playtest-discard-zone').textContent).toContain('1');

    mounted.unmount();
  });

  test('opening setup card actions can move cards between setup zones but not hand or board', async () => {
    const mounted = await mountPage();

    const manaChoices = [...testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll<HTMLButtonElement>('.playtest-opening-copy-button')];
    for (const button of manaChoices.slice(0, 3)) {
      button.click();
      await flushPage();
    }
    const acceptButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Setup board');
    acceptButton?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-opening-setup-cards')).not.toBeNull();

    testZone(mounted.container, 'playtest-library-zone').click();
    await flushPage();

    expect(document.body.querySelector('[data-testid="playtest-stack-overlay"]')).toBeNull();

    const stackCard = testZone(mounted.container, 'playtest-opening-library-browser')
      .querySelector<HTMLElement>('[data-instance-id]');
    expect(stackCard).not.toBeNull();
    const cardContext = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
      clientX: 30,
      clientY: 30,
    });
    stackCard?.dispatchEvent(cardContext);
    await flushPage();

    const cardMenuText = document.body.querySelector('[data-testid="playtest-context-menu"]')?.textContent ?? '';
    expect(cardMenuText).not.toContain('To Hand');
    expect(cardMenuText).toContain('To Discard');
    expect(cardMenuText).toContain('To Banish');
    expect(cardMenuText).toContain('To Hero');
    expect(cardMenuText).not.toContain('To Board');
    expect(cardMenuText).not.toContain('Copy');
    expect(cardMenuText).not.toContain('Flip');
    expect(cardMenuText).not.toContain('Delete');

    mounted.unmount();
  });

  test('opening hand phase does not allow stack cards to be moved into hand', async () => {
    const mounted = await mountPage();

    const manaChoices = [...testZone(mounted.container, 'playtest-opening-mana')
      .querySelectorAll<HTMLButtonElement>('.playtest-opening-copy-button')];
    for (const button of manaChoices.slice(0, 3)) {
      button.click();
      await flushPage();
    }
    const acceptManaButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.trim() === 'Setup board');
    acceptManaButton?.click();
    await flushPage();

    const drawHandButton = [...testZone(mounted.container, 'playtest-opening-setup-cards').querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Draw hand'));
    drawHandButton?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-opening-hand').querySelectorAll('[data-instance-id]')).toHaveLength(7);

    const stackContext = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
      clientX: 40,
      clientY: 40,
    });
    testZone(mounted.container, 'playtest-library-zone').dispatchEvent(stackContext);
    await flushPage();

    const stackMenuText = document.body.querySelector('[data-testid="playtest-context-menu"]')?.textContent ?? '';
    expect(stackMenuText).not.toContain('Open');
    expect(stackMenuText).not.toContain('Top to Hand');
    expect(stackMenuText).not.toContain('Top to Discard');
    expect(stackMenuText).not.toContain('Top to Banish');
    expect(stackMenuText).not.toContain('Top to Library');

    testZone(mounted.container, 'playtest-library-zone').click();
    await flushPage();

    const stackCard = document.body.querySelector<HTMLElement>('[data-testid="playtest-stack-overlay"] [data-instance-id]');
    expect(stackCard).toBeNull();

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
    const scaleInput = mounted.container.querySelector<HTMLInputElement>('.playtester-scale');
    const topbar = mounted.container.querySelector<HTMLElement>('.playtester-topbar');
    const undoButton = mounted.container.querySelector<HTMLButtonElement>('[data-testid="playtest-undo"]');
    const redoButton = mounted.container.querySelector<HTMLButtonElement>('[data-testid="playtest-redo"]');
    const topbarGroups = [...topbar?.children ?? []];
    expect(topbarGroups[0]?.textContent).toContain('Scale');
    expect(topbarGroups[0]?.contains(scaleInput)).toBe(true);
    expect(topbarGroups[0]?.contains(undoButton)).toBe(true);
    expect(topbarGroups[0]?.contains(redoButton)).toBe(true);
    const firstGroupChildren = [...topbarGroups[0]?.children ?? []];
    expect(firstGroupChildren[0]?.contains(undoButton)).toBe(true);
    expect(firstGroupChildren[0]?.contains(redoButton)).toBe(true);
    expect(firstGroupChildren[2]?.contains(scaleInput)).toBe(true);
    expect(topbarGroups[1]?.textContent).toContain('Next turn');
    expect(topbarGroups[1]?.textContent).toContain('Reset to Setup');
    expect(topbarGroups[1]?.textContent).toContain('Restart');
    expect(topbar?.textContent).toContain('Scale');
    expect(topbar?.contains(scaleInput)).toBe(true);
    expect(topbar?.contains(undoButton)).toBe(true);
    expect(topbar?.contains(redoButton)).toBe(true);
    expect(undoButton?.textContent?.trim()).toBe('');
    expect(redoButton?.textContent?.trim()).toBe('');
    expect(undoButton?.disabled).toBe(true);
    expect(redoButton?.disabled).toBe(true);
    expect(topbar?.querySelectorAll('.theme-pill')).toHaveLength(0);
    expect(topbar?.textContent).not.toContain('Library');
    expect(topbar?.textContent).not.toContain('Hand');
    expect(topbar?.textContent).not.toContain('Board');
    expect(mounted.container.querySelector('.playtester-footer')).toBeNull();
    expect(scaleInput?.value).toBe('0.75');
    expect(scaleInput?.min).toBe('0.5');
    expect(scaleInput?.max).toBe('1.6');

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    expect(mounted.container.querySelector('.playtest-card-face-animating')).toBeNull();
    handCard?.click();
    await flushPage();
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(6);
    expect(nonSetupBoardCards(testZone(mounted.container, 'playtest-board-zone'))).toHaveLength(1);
    expect(mounted.container.querySelector('.playtest-card-face-animating')).toBeNull();
    expect(undoButton?.disabled).toBe(false);
    expect(redoButton?.disabled).toBe(true);

    const playCard = nonSetupBoardCards(testZone(mounted.container, 'playtest-board-zone'))[0];
    playCard?.click();
    await flushPage();
    expect(playCard?.className).toContain('playtest-card-tapped');

    const nextTurnButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('.playtester-topbar button')]
      .find((button) => button.textContent?.includes('Next turn'));
    nextTurnButton?.click();
    await flushPage();

    const updatedPlayCard = nonSetupBoardCards(testZone(mounted.container, 'playtest-board-zone'))[0];
    expect(updatedPlayCard?.className).not.toContain('playtest-card-tapped');
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(7);

    mounted.unmount();
  });

  test('does not render placeholder cards when the active hand is empty', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    for (let count = 0; count < 7; count += 1) {
      testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
      await flushPage();
    }

    const handZone = testZone(mounted.container, 'playtest-hand-zone');
    expect(handZone.querySelectorAll('[data-instance-id]')).toHaveLength(0);
    expect(handZone.querySelectorAll('.playtester-hand-placeholder-card')).toHaveLength(0);

    mounted.unmount();
  });

  test('supports undo and redo for playtest state while preserving scale', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 500, 400));
    const scaleInput = mounted.container.querySelector<HTMLInputElement>('.playtester-scale');
    const undoButton = mounted.container.querySelector<HTMLButtonElement>('[data-testid="playtest-undo"]');
    const redoButton = mounted.container.querySelector<HTMLButtonElement>('[data-testid="playtest-redo"]');

    board.dispatchEvent(new WheelEvent('wheel', {
      bubbles: true,
      cancelable: true,
      altKey: true,
      deltaY: -100,
      clientX: 250,
      clientY: 200,
    }));
    await flushPage();
    expect(scaleInput?.value).toBe('0.8');

    testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(6);
    expect(nonSetupBoardCards(board)).toHaveLength(1);
    expect(undoButton?.disabled).toBe(false);
    expect(redoButton?.disabled).toBe(true);

    testZone(mounted.container, 'playtest-hero-zone').click();
    await flushPage();
    expect(document.body.querySelector('[data-testid="playtest-stack-overlay"]')).not.toBeNull();

    window.dispatchEvent(playtestKeyEvent('z', { ctrlKey: true }));
    await flushPage();

    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(7);
    expect(nonSetupBoardCards(board)).toHaveLength(0);
    expect(document.body.querySelector('[data-testid="playtest-stack-overlay"]')).toBeNull();
    expect(scaleInput?.value).toBe('0.8');
    expect(undoButton?.disabled).toBe(true);
    expect(redoButton?.disabled).toBe(false);

    window.dispatchEvent(playtestKeyEvent('y', { ctrlKey: true }));
    await flushPage();

    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(6);
    expect(nonSetupBoardCards(board)).toHaveLength(1);
    expect(undoButton?.disabled).toBe(false);
    expect(redoButton?.disabled).toBe(true);

    window.dispatchEvent(playtestKeyEvent('z', { ctrlKey: true }));
    await flushPage();
    window.dispatchEvent(playtestKeyEvent('Z', { ctrlKey: true, shiftKey: true }));
    await flushPage();
    expect(nonSetupBoardCards(board)).toHaveLength(1);

    window.dispatchEvent(playtestKeyEvent('z', { ctrlKey: true }));
    await flushPage();
    testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();

    expect(nonSetupBoardCards(board)).toHaveLength(1);
    expect(undoButton?.disabled).toBe(false);
    expect(redoButton?.disabled).toBe(true);

    mounted.unmount();
  });

  test('does not render sideboard reference UI on the active play surface', async () => {
    fetchDeckDetailMock.mockResolvedValueOnce({
      ...deckRecord,
      sideboards: [
        {
          id: 'sideboard-1',
          name: 'Sideboard',
          total_cards: 1,
          unique_cards: 1,
          entries: [{ quantity: 1, card }],
        },
      ],
    });
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    expect(mounted.container.textContent).not.toContain('Sideboard reference');
    expect(mounted.container.textContent).not.toContain('Sideboards 1');

    mounted.unmount();
  });

  test('middle-click hold zooms board cards until release or leave', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    handCard?.click();
    await flushPage();

    const playCard = nonSetupBoardCards(testZone(mounted.container, 'playtest-board-zone'))[0];
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

  test('reorders same-zone hand drops against the target after removing the source', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const handZone = testZone(mounted.container, 'playtest-hand-zone');
    const handCards = [...handZone.querySelectorAll<HTMLElement>('[data-instance-id]')];
    expect(handCards.length).toBeGreaterThanOrEqual(3);
    vi.spyOn(handCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(50, 450, 100, 140));
    vi.spyOn(handCards[2] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(250, 450, 100, 140));

    const orderBefore = handCards.map((element) => element.dataset.instanceId);
    const originalElementsFromPoint = document.elementsFromPoint;
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [handCards[2]],
    });

    handCards[0]?.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 13, clientX: 70, clientY: 470 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 13, clientX: 270, clientY: 470 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 13, clientX: 270, clientY: 470 }));
    await flushPage();

    const orderAfter = [...handZone.querySelectorAll<HTMLElement>('[data-instance-id]')]
      .map((element) => element.dataset.instanceId);
    expect(orderAfter.slice(0, 3)).toEqual([orderBefore[1], orderBefore[0], orderBefore[2]]);

    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: originalElementsFromPoint,
    });
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
    expect(nonSetupBoardCards(board)).toHaveLength(0);

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

    expect(nonSetupBoardCards(board)).toHaveLength(1);
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(6);
    const boardCard = nonSetupBoardWrappers(board)[0];
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

    const boardCards = nonSetupBoardCards(board);
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

    const boardWrappers = nonSetupBoardWrappers(board);
    expect(boardWrappers.map((element) => element.style.left)).toEqual(['74%', '90%']);
    expect(boardWrappers.map((element) => element.style.top)).toEqual(['22%', '22%']);

    mounted.unmount();
  });

  test('adds board cards to selection with shift click', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');

    testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();
    testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();

    const boardCards = nonSetupBoardCards(board);
    expect(boardCards).toHaveLength(2);

    boardCards[0]?.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 36, clientX: 100, clientY: 100, shiftKey: true }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 36, clientX: 100, clientY: 100, shiftKey: true }));
    boardCards[0]?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, shiftKey: true }));
    await flushPage();

    boardCards[1]?.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 37, clientX: 260, clientY: 100, shiftKey: true }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 37, clientX: 260, clientY: 100, shiftKey: true }));
    boardCards[1]?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, shiftKey: true }));
    await flushPage();

    const table = mounted.container.querySelector<HTMLElement>('.playtester-table');
    expect(table?.dataset.playtestSelectedCount).toBe('2');
    expect(board.querySelectorAll('[data-playtest-selected="true"]')).toHaveLength(2);
    expect(boardCards.every((element) => element.className.includes('playtest-card-selected'))).toBe(true);

    mounted.unmount();
  });

  test('groups selected board cards from the G hotkey', async () => {
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

    const boardCards = nonSetupBoardCards(board);
    expect(boardCards).toHaveLength(2);
    vi.spyOn(boardCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(60, 60, 100, 140));
    vi.spyOn(boardCards[1] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(220, 60, 100, 140));

    board.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 34, clientX: 40, clientY: 40 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 34, clientX: 340, clientY: 240 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 34, clientX: 340, clientY: 240 }));
    await flushPage();

    window.dispatchEvent(playtestKeyEvent('g'));
    await flushPage();

    expect(board.querySelectorAll('[data-testid="playtest-visual-pile"]')).toHaveLength(1);
    const draftAfter = JSON.parse(localStorage.getItem('card-reader.playtester.deck-1') ?? '{}');
    const groupedCards = getZoneInstances(draftAfter.state, 'play').filter((instance) =>
      boardCards.some((card) => card.dataset.instanceId === instance.instanceId),
    );

    expect(new Set(groupedCards.map((instance) => instance.pileGroupId)).size).toBe(1);
    expect(groupedCards.every((instance) => instance.pileGroupId !== null)).toBe(true);
    expect(groupedCards.map((instance) => instance.pileOrder)).toEqual([0, 1]);

    mounted.unmount();
  });

  test('clears drag overlays before creating a ctrl-drop visual pile', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 500, 400));

    testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();
    testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();

    const boardCards = nonSetupBoardCards(board);
    expect(boardCards).toHaveLength(2);
    vi.spyOn(boardCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(60, 60, 100, 140));
    vi.spyOn(boardCards[1] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(220, 60, 100, 140));

    const originalElementsFromPoint = document.elementsFromPoint;
    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: () => [boardCards[1], board],
    });

    boardCards[0]?.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 35, clientX: 100, clientY: 100 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 35, clientX: 260, clientY: 100, ctrlKey: true }));
    await flushPage();
    expect(document.body.querySelectorAll('[data-testid="playtest-dragged-card"]')).toHaveLength(1);

    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 35, clientX: 260, clientY: 100, ctrlKey: true }));
    await flushPage();

    expect(board.querySelectorAll('[data-testid="playtest-visual-pile"]')).toHaveLength(1);
    expect(document.body.querySelector('[data-testid="playtest-dragged-card"]')).toBeNull();

    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: originalElementsFromPoint,
    });
    mounted.unmount();
  });

  test('restores previous board selection when drag-box selection is cancelled', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 500, 400));

    testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();
    testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();

    const boardCards = nonSetupBoardCards(board);
    expect(boardCards).toHaveLength(2);
    vi.spyOn(boardCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(60, 60, 100, 140));
    vi.spyOn(boardCards[1] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(220, 60, 100, 140));

    board.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 31, clientX: 40, clientY: 40 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 31, clientX: 180, clientY: 240 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 31, clientX: 180, clientY: 240 }));
    await flushPage();

    expect([...board.querySelectorAll<HTMLElement>('[data-playtest-selected="true"]')]
      .map((element) => element.dataset.instanceId)).toEqual([boardCards[0]?.dataset.instanceId]);

    board.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 32, clientX: 200, clientY: 40 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 32, clientX: 360, clientY: 240 }));
    await flushPage();

    expect([...board.querySelectorAll<HTMLElement>('[data-playtest-selected="true"]')]
      .map((element) => element.dataset.instanceId)).toEqual([boardCards[1]?.dataset.instanceId]);

    window.dispatchEvent(playtestPointerEvent('pointercancel', { pointerId: 32, clientX: 360, clientY: 240 }));
    await flushPage();

    expect([...board.querySelectorAll<HTMLElement>('[data-playtest-selected="true"]')]
      .map((element) => element.dataset.instanceId)).toEqual([boardCards[0]?.dataset.instanceId]);

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

    const boardCards = nonSetupBoardCards(board);
    expect(boardCards).toHaveLength(2);
    vi.spyOn(boardCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(60, 60, 100, 140));
    vi.spyOn(boardCards[1] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(220, 60, 100, 140));

    board.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 11, clientX: 40, clientY: 40 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 11, clientX: 340, clientY: 240 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 11, clientX: 340, clientY: 240 }));
    await flushPage();

    const boardWrappersBefore = nonSetupBoardWrappers(board);
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

    const boardWrappersAfter = nonSetupBoardWrappers(board);
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
      const boardCards = nonSetupBoardCards(board);
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

    expect(nonSetupBoardCards(board)).toHaveLength(2);
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(5);

    boardCards = nonSetupBoardCards(board);
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

    expect(nonSetupBoardCards(board)).toHaveLength(0);
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(5);
    expect(testZone(mounted.container, 'playtest-discard-zone').textContent).toContain('2');

    Object.defineProperty(document, 'elementsFromPoint', {
      configurable: true,
      value: originalElementsFromPoint,
    });
    mounted.unmount();
  });

  test('handles playtester hotkeys and board wheel scale on the active play screen', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const board = testZone(mounted.container, 'playtest-board-zone');
    vi.spyOn(board, 'getBoundingClientRect').mockReturnValue(rect(0, 0, 500, 400));

    for (let count = 0; count < 2; count += 1) {
      testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]')?.click();
      await flushPage();
    }

    const boardCards = nonSetupBoardCards(board);
    expect(boardCards).toHaveLength(2);
    vi.spyOn(boardCards[0] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(60, 60, 100, 140));
    vi.spyOn(boardCards[1] as HTMLElement, 'getBoundingClientRect').mockReturnValue(rect(220, 60, 100, 140));

    board.dispatchEvent(playtestPointerEvent('pointerdown', { pointerId: 21, clientX: 40, clientY: 40 }));
    window.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 21, clientX: 340, clientY: 240 }));
    window.dispatchEvent(playtestPointerEvent('pointerup', { pointerId: 21, clientX: 340, clientY: 240 }));
    await flushPage();

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    handCard?.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    board.dispatchEvent(playtestPointerEvent('pointermove', { pointerId: 22, clientX: 250, clientY: 200 }));

    window.dispatchEvent(playtestKeyEvent('c', { ctrlKey: true }));
    window.dispatchEvent(playtestKeyEvent('v', { ctrlKey: true }));
    await flushPage();

    expect(nonSetupBoardCards(board)).toHaveLength(4);

    window.dispatchEvent(playtestKeyEvent('t'));
    await flushPage();
    expect([...board.querySelectorAll<HTMLElement>('[data-playtest-selected="true"]')]
      .every((element) => element.className.includes('playtest-card-tapped'))).toBe(true);

    expect(testZone(mounted.container, 'playtest-hand-zone').querySelector('.playtest-card-face-animating')).toBeNull();
    window.dispatchEvent(playtestKeyEvent('f'));
    await flushPage();
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelector('img[alt$="face down"]')).not.toBeNull();
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelector('.playtest-card-face-animating')).not.toBeNull();

    window.dispatchEvent(playtestKeyEvent('Delete'));
    await flushPage();
    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(4);

    const scaleInput = mounted.container.querySelector<HTMLInputElement>('.playtester-scale');
    board.dispatchEvent(new WheelEvent('wheel', {
      bubbles: true,
      cancelable: true,
      altKey: true,
      deltaY: -100,
      clientX: 250,
      clientY: 200,
    }));
    await flushPage();
    expect(scaleInput?.value).toBe('0.8');

    expect(mounted.container.querySelector('[data-testid="playtest-stack-overlay"]')).toBeNull();
    window.dispatchEvent(playtestKeyEvent('o'));
    await flushPage();
    expect(testZone(mounted.container, 'playtest-stack-overlay').textContent).toContain('Library');

    mounted.unmount();
  });

  test('shuffles the hovered stack from the R hotkey', async () => {
    createPlaytestDraftWithDiscardStack();
    const mounted = await mountPage();
    const discardZone = testZone(mounted.container, 'playtest-discard-zone');

    const draftBefore = JSON.parse(localStorage.getItem('card-reader.playtester.deck-1') ?? '{}');
    const libraryBefore = getZoneInstances(draftBefore.state, 'library').map((instance) => instance.instanceId);
    const discardBefore = getZoneInstances(draftBefore.state, 'discard').map((instance) => instance.instanceId);
    const randomMock = vi.spyOn(Math, 'random').mockReturnValue(0);

    window.dispatchEvent(playtestKeyEvent('r'));
    await flushPage();

    let draftAfter = JSON.parse(localStorage.getItem('card-reader.playtester.deck-1') ?? '{}');
    expect(getZoneInstances(draftAfter.state, 'library').map((instance) => instance.instanceId)).toEqual(libraryBefore);
    expect(getZoneInstances(draftAfter.state, 'discard').map((instance) => instance.instanceId)).toEqual(discardBefore);

    discardZone.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    await flushPage();
    window.dispatchEvent(playtestKeyEvent('r'));
    await flushPage();

    expect(discardZone.className).toContain('playtest-stack-shuffling');
    draftAfter = JSON.parse(localStorage.getItem('card-reader.playtester.deck-1') ?? '{}');
    const libraryAfter = getZoneInstances(draftAfter.state, 'library').map((instance) => instance.instanceId);
    const discardAfter = getZoneInstances(draftAfter.state, 'discard').map((instance) => instance.instanceId);

    expect(libraryAfter).toEqual(libraryBefore);
    expect(discardAfter).not.toEqual(discardBefore);
    expect([...discardAfter].sort()).toEqual([...discardBefore].sort());

    randomMock.mockRestore();
    mounted.unmount();
  });

  test('keeps active play hotkeys available from focused non-text controls and cards', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const hand = testZone(mounted.container, 'playtest-hand-zone');
    const board = testZone(mounted.container, 'playtest-board-zone');
    const scaleInput = mounted.container.querySelector<HTMLInputElement>('.playtester-scale');
    if (!scaleInput) {
      throw new Error('expected scale input');
    }

    expect(hand.querySelectorAll('[data-instance-id]')).toHaveLength(7);
    scaleInput.focus();
    expect(document.activeElement).toBe(scaleInput);
    scaleInput.dispatchEvent(playtestPointerEvent('pointerup'));
    await flushPage();
    expect(document.activeElement).not.toBe(scaleInput);

    const nextTurnButton = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('button'))
      .find((button) => button.textContent?.includes('Next turn'));
    if (!nextTurnButton) {
      throw new Error('expected next turn button');
    }
    nextTurnButton.focus();
    expect(document.activeElement).toBe(nextTurnButton);
    nextTurnButton.dispatchEvent(playtestPointerEvent('pointerup'));
    await flushPage();
    expect(document.activeElement).not.toBe(nextTurnButton);

    scaleInput.focus();
    scaleInput.dispatchEvent(playtestKeyEvent('d'));
    await flushPage();
    expect(hand.querySelectorAll('[data-instance-id]')).toHaveLength(8);

    hand.querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();

    const boardCard = nonSetupBoardCards(board)[0];
    if (!boardCard) {
      throw new Error('expected board card');
    }

    boardCard.focus();
    boardCard.dispatchEvent(playtestKeyEvent('t'));
    await flushPage();
    expect(nonSetupBoardCards(board)[0]?.className)
      .toContain('playtest-card-tapped');

    boardCard.dispatchEvent(playtestKeyEvent('f'));
    await flushPage();
    expect(nonSetupBoardCards(board)[0]?.querySelector('img[alt$="face down"]')).not.toBeNull();

    mounted.unmount();
  });

  test('pastes copied card snapshots after the source card changes or is deleted', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const hand = testZone(mounted.container, 'playtest-hand-zone');
    const handCard = hand.querySelector<HTMLElement>('[data-instance-id]');
    const sourceId = handCard?.dataset.instanceId;
    if (!handCard || !sourceId) {
      throw new Error('expected hand card');
    }
    const draftBefore = JSON.parse(localStorage.getItem('card-reader.playtester.deck-1') ?? '{}');
    const sourceCardId = draftBefore.state.instances.find((instance: { instanceId: string }) => instance.instanceId === sourceId)?.cardId;

    handCard.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    window.dispatchEvent(playtestKeyEvent('c', { ctrlKey: true }));
    window.dispatchEvent(playtestKeyEvent('f'));
    await flushPage();
    window.dispatchEvent(playtestKeyEvent('Delete'));
    await flushPage();
    window.dispatchEvent(playtestKeyEvent('v', { ctrlKey: true }));
    await flushPage();

    const draftAfter = JSON.parse(localStorage.getItem('card-reader.playtester.deck-1') ?? '{}');
    const pastedCopies = getZoneInstances(draftAfter.state, 'play')
      .filter((instance) => instance.cardId === sourceCardId);

    expect(draftAfter.state.instances.some((instance: { instanceId: string }) => instance.instanceId === sourceId)).toBe(false);
    expect(pastedCopies).toHaveLength(1);
    expect(pastedCopies[0]?.instanceId).not.toBe(sourceId);
    expect(pastedCopies[0]?.face).toBe('front');

    mounted.unmount();
  });

  test('draws, untaps, and advances turns from playtester hotkeys', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    const hand = testZone(mounted.container, 'playtest-hand-zone');
    const board = testZone(mounted.container, 'playtest-board-zone');

    expect(hand.querySelectorAll('[data-instance-id]')).toHaveLength(7);

    window.dispatchEvent(playtestKeyEvent('d'));
    await flushPage();
    expect(hand.querySelectorAll('[data-instance-id]')).toHaveLength(8);

    hand.querySelector<HTMLElement>('[data-instance-id]')?.click();
    await flushPage();

    let boardCard = nonSetupBoardCards(board)[0];
    expect(boardCard).not.toBeNull();
    expect(hand.querySelectorAll('[data-instance-id]')).toHaveLength(7);

    boardCard?.click();
    await flushPage();
    boardCard = nonSetupBoardCards(board)[0];
    expect(boardCard?.className).toContain('playtest-card-tapped');

    window.dispatchEvent(playtestKeyEvent('u'));
    await flushPage();
    boardCard = nonSetupBoardCards(board)[0];
    expect(boardCard?.className).not.toContain('playtest-card-tapped');
    expect(hand.querySelectorAll('[data-instance-id]')).toHaveLength(7);

    boardCard?.click();
    await flushPage();
    boardCard = nonSetupBoardCards(board)[0];
    expect(boardCard?.className).toContain('playtest-card-tapped');

    window.dispatchEvent(playtestKeyEvent('n'));
    await flushPage();
    boardCard = nonSetupBoardCards(board)[0];
    expect(boardCard?.className).not.toContain('playtest-card-tapped');
    expect(hand.querySelectorAll('[data-instance-id]')).toHaveLength(8);

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
    expect(stackMenuText).toContain('Open');
    expect(stackMenuText).not.toContain('Open Stack');

    const libraryContext = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
      clientX: 24,
      clientY: 24,
    });
    testZone(mounted.container, 'playtest-library-zone').dispatchEvent(libraryContext);
    await flushPage();

    const libraryMenu = document.body.querySelector<HTMLElement>('[data-testid="playtest-context-menu"]');
    const libraryMenuText = libraryMenu?.textContent ?? '';
    expect(libraryMenuText).toContain('Draw');
    expect(libraryMenuText).toContain('D');
    expect(libraryMenuText).toContain('Shuffle');
    expect(libraryMenuText).toContain('R');
    expect(libraryMenuText).toContain('Open');
    const openAction = Array.from(libraryMenu?.querySelectorAll('button') ?? []).find((action) => action.textContent?.includes('Open'));
    expect(openAction?.querySelector('.playtest-context-menu-hotkey')?.textContent).toContain('O');
    expect(libraryMenuText).not.toContain('Draw Top Card');
    expect(libraryMenuText).not.toContain('Shuffle Library');
    expect(libraryMenuText).not.toContain('Open Stack');

    const handCard = testZone(mounted.container, 'playtest-hand-zone').querySelector<HTMLElement>('[data-instance-id]');
    const cardContext = new MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 40, clientY: 40 });
    handCard?.dispatchEvent(cardContext);
    await flushPage();

    expect(cardContext.defaultPrevented).toBe(true);
    const cardMenu = document.body.querySelector<HTMLElement>('[data-testid="playtest-context-menu"]');
    expect(cardMenu?.textContent).toContain('Copy');
    expect(cardMenu?.textContent).toContain('Ctrl+C');
    expect(cardMenu?.textContent).toContain('Flip Down');
    expect(cardMenu?.textContent).toContain('F');
    expect(cardMenu?.textContent).toContain('Delete');
    expect(cardMenu?.textContent).toContain('Del');
    expect(cardMenu?.textContent).toContain('To Board');
    expect(cardMenu?.textContent).not.toContain('Move to Board');
    expect(cardMenu?.textContent).not.toContain('Move to Hero');
    expect(cardMenu?.querySelector('.playtest-context-menu-action-divider')).not.toBeNull();

    const handCountBeforeCopyPaste = testZone(mounted.container, 'playtest-hand-zone')
      .querySelectorAll('[data-instance-id]').length;
    const copyButton = [...cardMenu?.querySelectorAll<HTMLButtonElement>('button') ?? []]
      .find((button) => button.textContent?.includes('Copy'));
    copyButton?.click();
    await flushPage();

    window.dispatchEvent(playtestKeyEvent('v', { ctrlKey: true }));
    await flushPage();

    expect(testZone(mounted.container, 'playtest-hand-zone').querySelectorAll('[data-instance-id]')).toHaveLength(handCountBeforeCopyPaste);
    expect(nonSetupBoardCards(testZone(mounted.container, 'playtest-board-zone'))).toHaveLength(1);

    const refreshedCardContext = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
      clientX: 40,
      clientY: 40,
    });
    handCard?.dispatchEvent(refreshedCardContext);
    await flushPage();
    const refreshedCardMenu = document.body.querySelector<HTMLElement>('[data-testid="playtest-context-menu"]');
    const refreshedFlipButton = [...refreshedCardMenu?.querySelectorAll<HTMLButtonElement>('button') ?? []]
      .find((button) => button.textContent?.includes('Flip Down'));
    refreshedFlipButton?.click();
    await flushPage();

    expect(testZone(mounted.container, 'playtest-hand-zone').querySelector('img[alt$="face down"]')).not.toBeNull();

    mounted.unmount();
  });

  test('stack overlay cards stay draggable without button semantics', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    testZone(mounted.container, 'playtest-hero-zone').click();
    await flushPage();

    const overlay = document.body.querySelector<HTMLElement>('[data-testid="playtest-stack-overlay"]');
    expect(overlay?.querySelector('[data-instance-id]')).not.toBeNull();
    expect(overlay?.querySelector('[data-instance-id][role="button"]')).toBeNull();
    expect(overlay?.querySelector('[data-instance-id][tabindex]')).toBeNull();

    mounted.unmount();
  });

  test('keeps stack overlay open after dragging a card out', async () => {
    const mounted = await mountPage();
    await keepOpeningHand(mounted.container);

    testZone(mounted.container, 'playtest-hero-zone').click();
    await flushPage();

    const overlay = testZone(mounted.container, 'playtest-stack-overlay');
    const overlayCard = overlay.querySelector<HTMLElement>('[data-instance-id]');
    if (!overlayCard) {
      throw new Error('expected stack overlay card');
    }

    overlayCard.dispatchEvent(playtestPointerEvent('pointerdown', {
      clientX: 10,
      clientY: 10,
      pointerId: 9,
    }));
    window.dispatchEvent(playtestPointerEvent('pointermove', {
      clientX: 24,
      clientY: 24,
      pointerId: 9,
    }));
    await flushPage();

    expect(testZone(mounted.container, 'playtest-stack-overlay')).not.toBeNull();

    window.dispatchEvent(playtestPointerEvent('pointerup', {
      clientX: 24,
      clientY: 24,
      pointerId: 9,
    }));
    await flushPage();

    expect(testZone(mounted.container, 'playtest-stack-overlay')).not.toBeNull();

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

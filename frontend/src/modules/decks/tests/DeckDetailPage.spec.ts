/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import DeckDetailPage from '@/modules/decks/DeckDetailPage.vue';

const { authState, fetchDeckDetailMock, fetchMyDeckMock, apiGetMock, exportTtsDeckMock } = vi.hoisted(() => ({
  authState: {
    canAccessStaffRoutes: false,
    user: { id: 'user-1' } as { id: string } | null,
  },
  fetchDeckDetailMock: vi.fn(),
  fetchMyDeckMock: vi.fn(),
  apiGetMock: vi.fn(),
  exportTtsDeckMock: vi.fn<(...args: unknown[]) => Promise<void>>().mockResolvedValue(undefined),
}));

vi.mock('@/api/client', () => ({
  api: {
    get: apiGetMock,
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/modules/auth/authStore', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/modules/decks/api', () => ({
  fetchDeckDetail: fetchDeckDetailMock,
  fetchMyDeck: fetchMyDeckMock,
}));

vi.mock('@/composables/useDeckExport', () => ({
  useDeckExport: () => ({
    exportTtsDeck: exportTtsDeckMock,
  }),
}));

vi.mock('@/components/app/AppPageHeader.vue', () => ({
  default: defineComponent({
    props: {
      title: { type: String, required: true },
      subtitle: { type: String, default: undefined },
      subtitleClass: { type: String, default: undefined },
      backTo: { type: [String, Object], default: undefined },
      backLabel: { type: String, default: undefined },
    },
    setup(props, { slots }) {
      return () =>
        h('header', [
          h('h1', props.title),
          props.backTo && props.backLabel
            ? h('a', {
              href: typeof props.backTo === 'string'
                ? props.backTo
                : (props.backTo as { path?: string }).path,
              'aria-label': props.backLabel,
            }, 'Back')
            : null,
          slots.titleMeta ? h('div', { 'data-testid': 'header-title-meta' }, slots.titleMeta()) : null,
          slots.subtitle
            ? h('div', { class: props.subtitleClass, 'data-testid': 'header-subtitle' }, slots.subtitle())
            : props.subtitle
              ? h('p', { 'data-testid': 'header-subtitle' }, props.subtitle)
              : null,
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
    props: {
      groupByType: { type: Boolean, default: false },
      showGroupByTypeControl: { type: Boolean, default: false },
    },
    emits: ['update:groupByType'],
    setup(props, { emit }) {
      return () => h('div', { 'data-testid': 'gallery-options-menu' }, [
        props.showGroupByTypeControl
          ? h('label', { 'data-testid': 'group-by-type-option' }, [
            'Group by Type',
            h('input', {
              type: 'checkbox',
              checked: props.groupByType,
              onChange: (event: Event) => emit(
                'update:groupByType',
                (event.target as HTMLInputElement).checked,
              ),
            }),
          ])
          : null,
      ]);
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckManaCurve.vue', () => ({
  default: defineComponent({
    setup(_props, { slots }) {
      return () => h('div', { 'data-testid': 'mana-curve' }, slots['header-actions']?.());
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckManaDistribution.vue', () => ({
  default: defineComponent({
    props: {
      entries: { type: Array, required: true },
    },
    setup(props) {
      return () => h(
        'div',
        { 'data-testid': 'mana-distribution' },
        (props.entries as Array<{ card: { name: string } }>).map((entry) => entry.card.name).join(', '),
      );
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
  description: 'A carefully tuned deck.',
  long_description: 'Opening plan\n\nSideboard notes',
  difficulty: 'hard' as const,
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
  tags: [
    { id: 'role-tank', key: 'tank', label: 'Tank', kind: 'role' as const },
  ],
  pending_tag_suggestions: [],
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

const mountPage = async (path = '/decks/deck-1') => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/decks/:id', component: DeckDetailPage },
      { path: '/cards/:id', component: { template: '<div />' } },
      { path: '/decks', component: { template: '<div />' } },
      { path: '/my/decks', component: { template: '<div />' } },
      { path: '/my/decks/:id', component: { template: '<div />' } },
      { path: '/my/decks/:id/edit', component: { template: '<div />' } },
      { path: '/notifications', component: { template: '<div />' } },
    ],
  });
  await router.push(path);
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

const stubDesktopViewport = (matches: boolean): void => {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }) as MediaQueryList));
};

describe('DeckDetailPage type grouping', () => {
  beforeEach(() => {
    stubDesktopViewport(true);
    authState.canAccessStaffRoutes = false;
    authState.user = { id: 'user-1' };
    localStorage.clear();
    fetchDeckDetailMock.mockResolvedValue(deckRecord);
    fetchMyDeckMock.mockResolvedValue(deckRecord);
    apiGetMock.mockResolvedValue({ data: filtersPayload });
    exportTtsDeckMock.mockResolvedValue(undefined);
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  test('renders mainboard cards grouped by type order by default and exposes the option in view options', async () => {
    const mounted = await mountPage();

    expect(readTypeGroupKeys(mounted.container)).toEqual(['spell', 'creature', 'untyped', 'mana']);
    expect(mounted.container.querySelector('[data-testid="group-by-type-option"]')?.textContent).toContain('Group by Type');
    expect(mounted.container.querySelector<HTMLInputElement>('[data-testid="group-by-type-option"] input')?.checked).toBe(true);
    expect(mounted.container.querySelectorAll('[data-testid^="deck-card-"]')).toHaveLength(4);

    mounted.unmount();
  });

  test('renders deck tags in the header subtitle row and the owner as side-panel text', async () => {
    const mounted = await mountPage();
    const header = mounted.container.querySelector('header');
    const titleMeta = mounted.container.querySelector('[data-testid="header-title-meta"]');
    const subtitle = mounted.container.querySelector('[data-testid="header-subtitle"]');
    const owner = mounted.container.querySelector('[data-testid="deck-owner"]');

    expect(header?.textContent).toContain('Grouped Deck');
    expect(titleMeta).toBeNull();
    expect(subtitle?.textContent).toContain('Tank');
    expect(subtitle?.classList.contains('!mt-4')).toBe(true);
    expect(header?.textContent).not.toContain('Owner');
    expect(header?.textContent).not.toContain('By');
    expect(owner?.textContent).toContain('By Owner');

    mounted.unmount();
  });

  test('returns to notifications when opened from a notification action', async () => {
    const mounted = await mountPage('/my/decks/deck-1?return_to=notifications');

    const backLink = mounted.container.querySelector('a[aria-label="Back to Notifications"]');
    expect(backLink?.getAttribute('href')).toBe('/notifications');
    mounted.unmount();
  });

  test('shows difficulty beside deck metadata only when specified', async () => {
    const mounted = await mountPage();

    expect(mounted.container.querySelector('[data-testid="deck-difficulty"]')?.textContent)
      .toContain('Difficulty · Hard');
    mounted.unmount();

    fetchDeckDetailMock.mockResolvedValueOnce({ ...deckRecord, difficulty: null });
    const unspecifiedMounted = await mountPage();

    expect(unspecifiedMounted.container.querySelector('[data-testid="deck-difficulty"]')).toBeNull();
    unspecifiedMounted.unmount();
  });

  test('places the deck description below the hero and anchors mana controls above the footer', async () => {
    const mounted = await mountPage();
    const header = mounted.container.querySelector('header');
    const description = mounted.container.querySelector<HTMLElement>('[data-testid="deck-description"]');
    const manaSection = mounted.container.querySelector<HTMLElement>('[data-testid="deck-mana-section"]');
    const viewOptions = mounted.container.querySelector<HTMLElement>('[data-testid="gallery-options-menu"]');

    expect(header?.textContent).not.toContain('A carefully tuned deck.');
    expect(description?.textContent).toContain('Summary');
    expect(description?.textContent).toContain('A carefully tuned deck.');
    expect(manaSection?.classList.contains('!mt-auto')).toBe(true);
    expect(description?.compareDocumentPosition(manaSection as Node) ?? 0)
      .toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(manaSection?.compareDocumentPosition(viewOptions as Node) ?? 0)
      .toBe(Node.DOCUMENT_POSITION_FOLLOWING);

    mounted.unmount();
  });

  test('allows staff to open the editor for another users deck', async () => {
    authState.user = { id: 'staff-user' };
    authState.canAccessStaffRoutes = true;
    const mounted = await mountPage();
    const editLink = mounted.container.querySelector<HTMLAnchorElement>('a[aria-label="Edit deck"]');

    expect(editLink?.getAttribute('href')).toContain('/my/decks/deck-1/edit');

    mounted.unmount();
  });

  test('does not expose editing to unrelated non-staff users', async () => {
    authState.user = { id: 'other-user' };
    const mounted = await mountPage();

    expect(mounted.container.querySelector('[aria-label="Edit deck"]')).toBeNull();

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
    expect(mounted.container.querySelector<HTMLInputElement>('[data-testid="group-by-type-option"] input')?.checked).toBe(false);
    expect(mounted.container.querySelectorAll('[data-testid^="deck-card-"]')).toHaveLength(4);

    mounted.unmount();
  });

  test('updates deck grouping from the view options control', async () => {
    const mounted = await mountPage();
    const groupByTypeOption = mounted.container.querySelector<HTMLInputElement>(
      '[data-testid="group-by-type-option"] input',
    );
    if (!(groupByTypeOption instanceof HTMLInputElement)) {
      throw new Error('expected group-by-type view option');
    }

    groupByTypeOption.click();
    await nextTick();

    expect(readTypeGroupKeys(mounted.container)).toEqual([]);
    expect(groupByTypeOption.checked).toBe(false);
    expect(localStorage.getItem('card-reader.deck-detail-group-by-type')).toBe('false');

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

  test('opens long descriptions by default and toggles details from the full summary and mana surfaces', async () => {
    const mounted = await mountPage();
    const summarySection = mounted.container.querySelector<HTMLElement>('[data-testid="deck-description"]');
    const manaSection = mounted.container.querySelector<HTMLElement>(
      '[data-testid="deck-mana-details-button"]',
    );
    if (!(summarySection instanceof HTMLElement) || !(manaSection instanceof HTMLElement)) {
      throw new Error('expected interactive summary and mana sections');
    }

    expect(window.matchMedia).toHaveBeenCalledWith('(min-width: 1536px)');
    const longDescription = mounted.container.querySelector<HTMLElement>('[data-testid="deck-long-description"]');
    expect(summarySection.getAttribute('aria-expanded')).toBe('true');
    expect(manaSection.getAttribute('aria-expanded')).toBe('false');
    expect(mounted.container.querySelector('.deck-detail-layout-expanded')).not.toBeNull();
    expect(longDescription?.textContent).toContain('About this deck');
    expect(longDescription?.textContent).toContain('Opening plan\n\nSideboard notes');
    expect(longDescription?.querySelector('p')?.classList.contains('whitespace-pre-wrap')).toBe(true);
    expect(longDescription?.querySelector('p')?.classList.contains('break-words')).toBe(true);
    expect(mounted.container.querySelector('[data-testid="mana-distribution"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="deck-detail-close-button"]')).not.toBeNull();

    summarySection.querySelector('p')?.click();
    await nextTick();

    expect(summarySection.getAttribute('aria-expanded')).toBe('false');

    summarySection.querySelector('p')?.click();
    await nextTick();

    manaSection.querySelector('[data-testid="mana-curve"]')?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await nextTick();

    expect(summarySection.getAttribute('aria-expanded')).toBe('false');
    expect(manaSection.getAttribute('aria-expanded')).toBe('true');
    expect(mounted.container.querySelector('[data-testid="deck-long-description"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="mana-distribution"]')?.textContent).toContain('Spell Card');
    expect(mounted.container.querySelector('[data-testid="deck-detail-close-button"]')).not.toBeNull();

    const sideboardButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Sideboard'),
    );
    if (!(sideboardButton instanceof HTMLButtonElement)) {
      throw new Error('expected sideboard tab');
    }
    sideboardButton.click();
    await nextTick();

    expect(mounted.container.querySelector('[data-testid="mana-distribution"]')?.textContent).toBe('Attachment Card');

    mounted.container.querySelector<HTMLButtonElement>('[data-testid="deck-detail-close-button"]')?.click();
    await nextTick();

    expect(manaSection.getAttribute('aria-expanded')).toBe('false');
    expect(mounted.container.querySelector('.deck-detail-layout-expanded')).toBeNull();
    mounted.unmount();
  });

  test('keeps long descriptions collapsed initially below the auto-expand breakpoint', async () => {
    stubDesktopViewport(false);
    const mounted = await mountPage();
    const summarySection = mounted.container.querySelector<HTMLElement>('[data-testid="deck-description"]');

    expect(summarySection?.getAttribute('aria-expanded')).toBe('false');
    expect(mounted.container.querySelector('[data-testid="deck-long-description"]')).toBeNull();
    expect(mounted.container.querySelector('.deck-detail-layout-expanded')).toBeNull();

    summarySection?.click();
    await nextTick();

    expect(summarySection?.getAttribute('aria-expanded')).toBe('true');
    expect(mounted.container.querySelector('[data-testid="deck-long-description"]')).not.toBeNull();

    mounted.unmount();
  });

  test('keeps the details pane mana-only when no long description is present', async () => {
    fetchDeckDetailMock.mockResolvedValueOnce({ ...deckRecord, long_description: null });
    const mounted = await mountPage();
    const manaDetailsButton = mounted.container.querySelector<HTMLElement>(
      '[data-testid="deck-mana-details-button"]',
    );

    expect(mounted.container.querySelector('[data-testid="deck-summary-details-button"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="deck-long-description"]')).toBeNull();
    expect(mounted.container.querySelector('.deck-detail-distribution-aside')).toBeNull();

    manaDetailsButton?.click();
    await nextTick();

    expect(mounted.container.querySelector('[data-testid="deck-long-description"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="mana-distribution"]')).not.toBeNull();
    expect(mounted.container.querySelector('.deck-detail-distribution-aside')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="deck-detail-close-button"]')).not.toBeNull();

    mounted.unmount();
  });

  test('renders compact labelled header actions and exports the active board to TTS', async () => {
    const mounted = await mountPage();
    const mainboardExportButton = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Copy Mainboard TTS"]',
    );
    if (!(mainboardExportButton instanceof HTMLButtonElement)) {
      throw new Error('expected mainboard export button');
    }

    expect(mounted.container.querySelector('button[aria-label="Copy share link"]')).not.toBeNull();
    expect(mounted.container.querySelector('a[aria-label="Edit deck"]')).not.toBeNull();
    expect(mounted.container.querySelector('button[aria-label="Copy share link"]')?.textContent).toBe('Share');
    expect(mainboardExportButton.textContent).toBe('TTS');
    expect(mounted.container.querySelector('a[aria-label="Edit deck"]')?.textContent).toBe('Edit');
    const playtestLink = Array.from(mounted.container.querySelectorAll<HTMLAnchorElement>('header a')).find(
      (link) => link.textContent?.trim() === 'Playtest',
    );
    const headerLinks = Array.from(mounted.container.querySelectorAll<HTMLAnchorElement>('header a'));
    expect(playtestLink).not.toBeNull();
    expect(playtestLink?.getAttribute('aria-label')).toBe('Playtest deck');
    expect(playtestLink).toBe(headerLinks[headerLinks.length - 1]);
    const headerActions = mounted.container.querySelectorAll<HTMLElement>('.app-header-action');
    expect(headerActions).toHaveLength(4);
    expect(Array.from(headerActions).every((action) => action.classList.contains('h-10'))).toBe(true);
    expect(mounted.container.querySelector('header')?.textContent).not.toContain('Copy Mainboard TTS');

    mainboardExportButton.click();
    await nextTick();

    expect(exportTtsDeckMock).toHaveBeenLastCalledWith('deck-1', {
      successMessage: 'TTS mainboard copied to clipboard',
    });

    const sideboardButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Sideboard'),
    );
    if (!(sideboardButton instanceof HTMLButtonElement)) {
      throw new Error('expected sideboard tab');
    }

    sideboardButton.click();
    await nextTick();

    const sideboardExportButton = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Copy Sideboard TTS"]',
    );
    if (!(sideboardExportButton instanceof HTMLButtonElement)) {
      throw new Error('expected sideboard export button');
    }

    sideboardExportButton.click();
    await nextTick();

    expect(exportTtsDeckMock).toHaveBeenLastCalledWith('deck-1', {
      sideboardId: 'side-1',
      successMessage: 'TTS sideboard copied to clipboard',
    });

    mounted.unmount();
  });
});

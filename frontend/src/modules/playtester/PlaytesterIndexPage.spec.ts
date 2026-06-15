/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import PlaytesterIndexPage from '@/modules/playtester/PlaytesterIndexPage.vue';
import { createInitialPlaytestState, getZoneInstances, serializePlaytestDraft } from '@/modules/playtester/playtestState';

const {
  authState,
  fetchDeckDetailMock,
  fetchCurrentCardBackMock,
  fetchMyDeckMock,
  fetchMyDeckSummariesMock,
  fetchPublicDeckSummariesMock,
} = vi.hoisted(() => ({
  authState: {
    authEnabled: true,
    authenticated: true,
  },
  fetchDeckDetailMock: vi.fn(),
  fetchCurrentCardBackMock: vi.fn(),
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
    setup(props) {
      return () => h('header', h('h1', props.title));
    },
  }),
}));

vi.mock('@/components/decks/DeckLoadingSkeleton.vue', () => ({
  default: defineComponent({
    props: {
      density: { type: String, default: 'default' },
    },
    setup(props) {
      return () => h('div', {
        class: [
          'deck-loading-skeleton',
          props.density === 'compact' ? 'deck-loading-skeleton-compact' : '',
        ],
      });
    },
  }),
}));

const buildDeck = (id: string, name: string, heroName: string, owner = 'owner') => ({
  id,
  name,
  description: null,
  visibility: 'public' as const,
  owner: { id: `${owner}-id`, username: owner },
  hero_card: {
    id: `${id}-hero`,
    key: `${id}-hero`,
    label: heroName,
    result_type: 'card' as const,
    image_url: null,
    name: heroName,
    symbols: [],
  },
  mainboard: {
    total_cards: 1,
    unique_cards: 1,
  },
  sideboard_count: 0,
  status: {
    is_valid: true,
    label: 'Ready',
    deprecated_card_count: 0,
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});

const buildCard = (id: string, name: string, imageUrl: string | null = null) => ({
  id,
  key: id,
  label: name,
  result_type: 'card' as const,
  image_url: imageUrl,
  name,
  is_hero: false,
  template_id: 'template',
  version_id: `${id}-version`,
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  type_line: 'Unit',
  mana_cost: '',
  mana_symbols: [],
  mana_value: null,
  attack: null,
  health: null,
  rules_text: '',
  confidence: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  types: [],
  symbols: [],
});

const buildDeckDetail = (id: string, name: string, heroName: string, owner = 'owner') => {
  const heroCard = {
    ...buildCard(`${id}-hero`, heroName),
    is_hero: true,
    type_line: 'Hero',
  };
  return {
    id,
    name,
    description: null,
    visibility: 'public' as const,
    owner: { id: `${owner}-id`, username: owner },
    hero_card: heroCard,
    mainboard: {
      total_cards: 10,
      unique_cards: 10,
      entries: Array.from({ length: 10 }, (_, index) => ({
        quantity: 1,
        card: buildCard(`${id}-card-${index + 1}`, `${name} Card ${index + 1}`, `/cards/${id}-${index + 1}.webp`),
      })),
    },
    sideboards: [],
    totals: {
      overall_total_cards: 10,
      overall_unique_cards: 10,
      mainboard_total_cards: 10,
      mainboard_unique_cards: 10,
    },
    status: {
      is_valid: true,
      label: 'Ready',
      issues: [],
      warnings: [],
      deprecated_card_count: 0,
      deprecated_card_ids: [],
    },
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
};

const createDeferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
};

const flushPage = async (): Promise<void> => {
  await nextTick();
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
  await nextTick();
};

const mountPage = async (): Promise<{
  container: HTMLElement;
  router: ReturnType<typeof createRouter>;
  unmount: () => void;
}> => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/playtester', component: PlaytesterIndexPage },
      { path: '/playtester/:deckId', component: { template: '<div />' } },
    ],
  });
  await router.push('/playtester');
  await router.isReady();
  const app = createApp(PlaytesterIndexPage);
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

describe('PlaytesterIndexPage', () => {
  beforeEach(() => {
    localStorage.clear();
    authState.authEnabled = true;
    authState.authenticated = true;
    fetchCurrentCardBackMock.mockResolvedValue({ current: { image_url: '/card-backs/current.webp' } });
    fetchMyDeckMock.mockImplementation((deckId: string) =>
      Promise.resolve(buildDeckDetail(deckId, deckId === 'owned' ? 'Owned Tempo' : 'Public Control', deckId === 'owned' ? 'Owned Hero' : 'Public Hero', deckId === 'owned' ? 'me' : 'other')),
    );
    fetchDeckDetailMock.mockImplementation((deckId: string) =>
      Promise.resolve(buildDeckDetail(deckId, deckId === 'owned' ? 'Owned Tempo' : 'Public Control', deckId === 'owned' ? 'Owned Hero' : 'Public Hero', deckId === 'owned' ? 'me' : 'other')),
    );
    fetchMyDeckSummariesMock.mockResolvedValue([buildDeck('owned', 'Owned Tempo', 'Owned Hero', 'me')]);
    fetchPublicDeckSummariesMock.mockResolvedValue([buildDeck('public', 'Public Control', 'Public Hero', 'other')]);
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  test('renders the pre-setup playtester shell on the deck selector route', async () => {
    const mounted = await mountPage();

    expect(mounted.container.querySelector('[data-testid="playtester-pre-setup-surface"]')).not.toBeNull();
    expect(mounted.container.textContent).toContain('Board');
    expect(mounted.container.textContent).toContain('Opening hand');
    expect(mounted.container.textContent).toContain('Select a deck to start setup.');
    expect(fetchCurrentCardBackMock).toHaveBeenCalledTimes(1);
    expect(mounted.container.querySelectorAll<HTMLImageElement>('.playtester-hand-placeholder-card img')).toHaveLength(7);
    expect(mounted.container.querySelector<HTMLImageElement>('.playtester-hand-placeholder-card img')?.src).toContain('/card-backs/current.webp');
    expect(mounted.container.querySelector('[data-testid="playtest-hero-zone"]')?.textContent).toContain('Hero');
    expect(mounted.container.querySelector('[data-testid="playtest-hero-zone"]')?.textContent).toContain('0');
    expect(mounted.container.querySelector('[data-testid="playtest-other-zone"]')).toBeNull();

    mounted.unmount();
  });

  test('uses stored playtester card scale on the selector surface', async () => {
    localStorage.setItem('card-reader.playtester.card-scale', '1.2');
    const mounted = await mountPage();
    const surface = mounted.container.querySelector<HTMLElement>('[data-testid="playtester-pre-setup-surface"]');

    expect(surface?.getAttribute('style')).toContain('--playtest-card-width: 11.70rem');
    expect(surface?.getAttribute('style')).toContain('--playtest-stack-full-width: 13.62rem');

    mounted.unmount();
  });

  test('updates stored playtester card scale from Alt wheel on the selector surface', async () => {
    const mounted = await mountPage();
    const surface = mounted.container.querySelector<HTMLElement>('[data-testid="playtester-pre-setup-surface"]');
    if (!surface) {
      throw new Error('expected selector surface');
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

    mounted.unmount();
  });

  test('renders owned suggestions before public suggestions for signed-in users', async () => {
    const mounted = await mountPage();
    const text = mounted.container.textContent ?? '';

    expect(fetchMyDeckSummariesMock).toHaveBeenCalledTimes(1);
    expect(fetchPublicDeckSummariesMock).toHaveBeenCalledTimes(1);
    expect(text.indexOf('Owned Tempo')).toBeGreaterThan(-1);
    expect(text.indexOf('Public Control')).toBeGreaterThan(-1);
    expect(text.indexOf('Owned Tempo')).toBeLessThan(text.indexOf('Public Control'));
    expect(mounted.container.textContent).toContain('Start Playtest');
    expect(mounted.container.querySelectorAll('[data-testid="deck-compact-card"]')).toHaveLength(2);
    expect(fetchMyDeckMock).toHaveBeenCalledWith('owned');
    expect(fetchMyDeckMock).toHaveBeenCalledWith('public');

    mounted.unmount();
  });

  test('searches suggestions through summary API params', async () => {
    vi.useFakeTimers();
    const mounted = await mountPage();
    const input = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Search by deck, hero, owner, or card"]');
    if (!input) {
      throw new Error('expected search input');
    }
    fetchMyDeckSummariesMock.mockResolvedValueOnce([buildDeck('owned', 'Owned Tempo', 'Owned Hero', 'me')]);
    fetchPublicDeckSummariesMock.mockResolvedValueOnce([]);

    input.value = 'Blade';
    input.dispatchEvent(new Event('input'));
    await vi.advanceTimersByTimeAsync(300);
    await flushPage();

    const ownedParams = fetchMyDeckSummariesMock.mock.calls.at(-1)?.[0];
    const publicParams = fetchPublicDeckSummariesMock.mock.calls.at(-1)?.[0];
    expect(ownedParams).toBeInstanceOf(URLSearchParams);
    expect(publicParams).toBeInstanceOf(URLSearchParams);
    expect((ownedParams as URLSearchParams).get('q')).toBe('Blade');
    expect((publicParams as URLSearchParams).get('q')).toBe('Blade');
    expect(mounted.container.textContent).toContain('Owned Tempo');
    expect(mounted.container.textContent).not.toContain('Public Control');

    mounted.unmount();
  });

  test('does not render stale suggestions while debounced search is pending', async () => {
    vi.useFakeTimers();
    const ownedDeferred = createDeferred<ReturnType<typeof buildDeck>[]>();
    const publicDeferred = createDeferred<ReturnType<typeof buildDeck>[]>();
    fetchMyDeckSummariesMock.mockReturnValueOnce(ownedDeferred.promise);
    fetchPublicDeckSummariesMock.mockReturnValueOnce(publicDeferred.promise);
    const mounted = await mountPage();
    const input = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Search by deck, hero, owner, or card"]');
    if (!input) {
      throw new Error('expected search input');
    }

    input.value = 'Blade';
    input.dispatchEvent(new Event('input'));
    await flushPage();
    ownedDeferred.resolve([buildDeck('stale-owned', 'Stale Owned', 'Old Hero', 'me')]);
    publicDeferred.resolve([buildDeck('stale-public', 'Stale Public', 'Old Hero', 'other')]);
    await flushPage();

    expect(mounted.container.textContent).not.toContain('Stale Owned');
    expect(mounted.container.textContent).not.toContain('Stale Public');
    expect(mounted.container.querySelectorAll('.deck-loading-skeleton')).toHaveLength(4);
    expect(mounted.container.querySelectorAll('.deck-loading-skeleton-compact')).toHaveLength(4);

    await vi.advanceTimersByTimeAsync(300);
    await flushPage();

    mounted.unmount();
  });

  test('deduplicates owned and public search results after server search', async () => {
    vi.useFakeTimers();
    const mounted = await mountPage();
    const input = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Search by deck, hero, owner, or card"]');
    if (!input) {
      throw new Error('expected search input');
    }
    const ownedDeck = buildDeck('shared', 'Shared Search Deck', 'Owned Hero', 'me');
    fetchMyDeckSummariesMock.mockResolvedValueOnce([ownedDeck]);
    fetchPublicDeckSummariesMock.mockResolvedValueOnce([ownedDeck, buildDeck('public-extra', 'Public Extra', 'Public Hero', 'other')]);

    input.value = 'Shared';
    input.dispatchEvent(new Event('input'));
    await vi.advanceTimersByTimeAsync(300);
    await flushPage();

    expect(mounted.container.textContent).toContain('Shared Search Deck');
    expect(mounted.container.textContent).toContain('Public Extra');
    expect((mounted.container.textContent?.match(/Shared Search Deck/g) ?? [])).toHaveLength(1);

    mounted.unmount();
  });

  test('does not fetch owned decks for anonymous users', async () => {
    authState.authenticated = false;
    const mounted = await mountPage();

    expect(fetchMyDeckSummariesMock).not.toHaveBeenCalled();
    expect(fetchPublicDeckSummariesMock).toHaveBeenCalledTimes(1);
    expect(mounted.container.textContent).not.toContain('Your Decks');
    expect(mounted.container.textContent).toContain('Public Control');
    expect(mounted.container.textContent).toContain('Start Playtest');

    mounted.unmount();
  });

  test('does not duplicate owned decks that are hidden past the visible owned limit', async () => {
    const ownedDecks = Array.from({ length: 7 }, (_, index) =>
      buildDeck(`owned-${index + 1}`, `Owned ${index + 1}`, `Owned Hero ${index + 1}`, 'me'),
    );
    fetchMyDeckSummariesMock.mockResolvedValue(ownedDecks);
    fetchPublicDeckSummariesMock.mockResolvedValue([
      ownedDecks[6],
      buildDeck('public-extra', 'Public Extra', 'Public Hero', 'other'),
    ]);

    const mounted = await mountPage();

    expect(mounted.container.textContent).toContain('Owned 1');
    expect(mounted.container.textContent).not.toContain('Owned 7');
    expect(mounted.container.textContent).toContain('Public Extra');

    mounted.unmount();
  });

  test('selects a deck without routing and starts the selected playtest from the footer action', async () => {
    const mounted = await mountPage();
    const ownedOption = [...mounted.container.querySelectorAll<HTMLButtonElement>('[data-testid="deck-compact-card"]')]
      .find((button) => button.textContent?.includes('Owned Tempo'));
    if (!ownedOption) {
      throw new Error('expected owned deck option');
    }

    ownedOption.click();
    await flushPage();

    expect(mounted.router.currentRoute.value.fullPath).toBe('/playtester');
    expect(fetchMyDeckMock).toHaveBeenCalledWith('owned');
    expect(ownedOption.getAttribute('aria-pressed')).toBe('true');
    expect(mounted.container.textContent).toContain('Hero: Owned Hero');
    expect(mounted.container.textContent).toContain('Opening hand: 7');
    const previewHandIds = [...mounted.container.querySelectorAll<HTMLElement>('[data-testid="playtest-hand-zone"] [data-instance-id]')]
      .map((element) => element.dataset.instanceId);
    const libraryStack = mounted.container.querySelector<HTMLElement>('[data-testid="playtest-library-zone"]');
    const heroStack = mounted.container.querySelector<HTMLElement>('[data-testid="playtest-hero-zone"]');
    expect(libraryStack?.querySelector('.playtest-stack-card img')?.getAttribute('src')).toContain('/card-backs/current.webp');
    expect(libraryStack?.querySelector('.playtest-stack-count')?.textContent).toBe('3');
    expect(heroStack?.querySelector('.playtest-stack-no-image')?.textContent).toContain('Owned Hero');
    expect(heroStack?.querySelector('.playtest-stack-count')?.textContent).toBe('1');
    libraryStack?.click();
    await flushPage();
    expect(mounted.container.querySelector('[data-testid="playtester-selector-stack-overlay"]')?.textContent).toContain('Library');
    expect(mounted.container.querySelector('[data-testid="playtester-selector-stack-overlay"]')?.textContent).toContain('3 cards');

    const startButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Start Playtest'));
    if (!startButton) {
      throw new Error('expected start button');
    }
    const pushSpy = vi.spyOn(mounted.router, 'push');
    expect(startButton.disabled).toBe(false);
    startButton.click();
    await flushPage();

    expect(pushSpy).toHaveBeenCalledWith('/playtester/owned');
    const storedDraft = JSON.parse(localStorage.getItem('card-reader.playtester.owned') ?? '{}');
    expect(getZoneInstances(storedDraft.state, 'hand').map((instance) => instance.instanceId)).toEqual(previewHandIds);
    expect(getZoneInstances(storedDraft.state, 'library')).toHaveLength(3);

    mounted.unmount();
  });

  test('shows continue and new playtest actions when the selected deck has a current draft', async () => {
    const draft = serializePlaytestDraft(createInitialPlaytestState(
      buildDeckDetail('owned', 'Owned Tempo', 'Owned Hero', 'me'),
      () => 0,
    ));
    localStorage.setItem('card-reader.playtester.owned', JSON.stringify(draft));
    const mounted = await mountPage();
    const ownedOption = [...mounted.container.querySelectorAll<HTMLButtonElement>('[data-testid="deck-compact-card"]')]
      .find((button) => button.textContent?.includes('Owned Tempo'));
    if (!ownedOption) {
      throw new Error('expected owned deck option');
    }

    ownedOption.click();
    await flushPage();

    expect(mounted.container.textContent).toContain('Continue Playtest');
    expect(mounted.container.textContent).toContain('New Playtest');
    const pushSpy = vi.spyOn(mounted.router, 'push');
    const continueButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('Continue Playtest'));
    const newButton = [...mounted.container.querySelectorAll<HTMLButtonElement>('button')]
      .find((button) => button.textContent?.includes('New Playtest'));
    if (!continueButton || !newButton) {
      throw new Error('expected continue and new playtest buttons');
    }

    continueButton.click();
    await flushPage();

    expect(pushSpy).toHaveBeenCalledWith('/playtester/owned');
    expect(localStorage.getItem('card-reader.playtester.owned')).not.toBeNull();

    pushSpy.mockClear();
    const previewHandIds = [...mounted.container.querySelectorAll<HTMLElement>('[data-testid="playtest-hand-zone"] [data-instance-id]')]
      .map((element) => element.dataset.instanceId);
    newButton.click();
    await flushPage();

    expect(pushSpy).toHaveBeenCalledWith('/playtester/owned');
    const newDraft = JSON.parse(localStorage.getItem('card-reader.playtester.owned') ?? '{}');
    expect(getZoneInstances(newDraft.state, 'hand').map((instance) => instance.instanceId)).toEqual(previewHandIds);
    expect(getZoneInstances(newDraft.state, 'library')).toHaveLength(3);

    mounted.unmount();
  });
});

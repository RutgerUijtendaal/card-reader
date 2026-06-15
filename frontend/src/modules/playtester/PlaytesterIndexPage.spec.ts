/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import PlaytesterIndexPage from '@/modules/playtester/PlaytesterIndexPage.vue';

const {
  authState,
  fetchCurrentCardBackMock,
  fetchMyDeckSummariesMock,
  fetchPublicDeckSummariesMock,
} = vi.hoisted(() => ({
  authState: {
    authEnabled: true,
    authenticated: true,
  },
  fetchCurrentCardBackMock: vi.fn(),
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
    setup() {
      return () => h('div', { class: 'deck-loading-skeleton' });
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
    authState.authEnabled = true;
    authState.authenticated = true;
    fetchCurrentCardBackMock.mockResolvedValue({ current: { image_url: '/card-backs/current.webp' } });
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
    expect(mounted.container.querySelectorAll<HTMLImageElement>('.playtester-selector-hand-card img')).toHaveLength(7);
    expect(mounted.container.querySelector<HTMLImageElement>('.playtester-selector-hand-card img')?.src).toContain('/card-backs/current.webp');

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
    expect(ownedOption.getAttribute('aria-pressed')).toBe('true');
    expect(mounted.container.textContent).toContain('Hero: Owned Hero');

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

    mounted.unmount();
  });
});

/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import PlaytesterIndexPage from '@/modules/playtester/PlaytesterIndexPage.vue';

const {
  authState,
  fetchMyDecksMock,
  fetchPublicDecksMock,
} = vi.hoisted(() => ({
  authState: {
    authEnabled: true,
    authenticated: true,
  },
  fetchMyDecksMock: vi.fn(),
  fetchPublicDecksMock: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/modules/auth/authStore', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/modules/decks/api', () => ({
  fetchMyDecks: fetchMyDecksMock,
  fetchPublicDecks: fetchPublicDecksMock,
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
    is_hero: true,
    lifecycle_status: 'active' as const,
    template_id: '',
    version_id: `${id}-hero-version`,
    version_number: 1,
    previous_version_id: null,
    is_latest: true,
    name: heroName,
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
  },
  mainboard: {
    total_cards: 1,
    unique_cards: 1,
    entries: [
      {
        quantity: 1,
        card: {
          id: `${id}-card`,
          key: `${id}-card`,
          label: 'Blade',
          result_type: 'card' as const,
          image_url: null,
          is_hero: false,
          lifecycle_status: 'active' as const,
          template_id: '',
          version_id: `${id}-card-version`,
          version_number: 1,
          previous_version_id: null,
          is_latest: true,
          name: 'Blade',
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
        },
      },
    ],
  },
  sideboards: [],
  totals: {
    overall_total_cards: 1,
    overall_unique_cards: 1,
    mainboard_total_cards: 1,
    mainboard_unique_cards: 1,
  },
  status: {
    is_valid: true,
    label: 'Ready',
    issues: [],
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});

const flushPage = async (): Promise<void> => {
  await nextTick();
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
  await nextTick();
};

const mountPage = async (): Promise<{ container: HTMLElement; unmount: () => void }> => {
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
    fetchMyDecksMock.mockResolvedValue([buildDeck('owned', 'Owned Tempo', 'Owned Hero', 'me')]);
    fetchPublicDecksMock.mockResolvedValue([buildDeck('public', 'Public Control', 'Public Hero', 'other')]);
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('renders owned suggestions before public suggestions for signed-in users', async () => {
    const mounted = await mountPage();
    const text = mounted.container.textContent ?? '';

    expect(fetchMyDecksMock).toHaveBeenCalledTimes(1);
    expect(fetchPublicDecksMock).toHaveBeenCalledTimes(1);
    expect(text.indexOf('Owned Tempo')).toBeGreaterThan(-1);
    expect(text.indexOf('Public Control')).toBeGreaterThan(-1);
    expect(text.indexOf('Owned Tempo')).toBeLessThan(text.indexOf('Public Control'));
    expect(mounted.container.textContent).toContain('Start Playtest');
    expect(
      mounted.container.querySelector('[data-navigation-target="/playtester/owned"]'),
    ).not.toBeNull();
    expect(
      mounted.container.querySelector('[data-navigation-target="/playtester/public"]'),
    ).not.toBeNull();

    mounted.unmount();
  });

  test('filters suggestions by included card names', async () => {
    const mounted = await mountPage();
    const input = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Search by deck, hero, owner, or card"]');
    if (!input) {
      throw new Error('expected search input');
    }

    input.value = 'Blade';
    input.dispatchEvent(new Event('input'));
    await flushPage();

    expect(mounted.container.textContent).toContain('Owned Tempo');
    expect(mounted.container.textContent).toContain('Public Control');

    input.value = 'Owned Hero';
    input.dispatchEvent(new Event('input'));
    await flushPage();

    expect(mounted.container.textContent).toContain('Owned Tempo');
    expect(mounted.container.textContent).not.toContain('Public Control');

    mounted.unmount();
  });

  test('does not fetch owned decks for anonymous users', async () => {
    authState.authenticated = false;
    const mounted = await mountPage();

    expect(fetchMyDecksMock).not.toHaveBeenCalled();
    expect(fetchPublicDecksMock).toHaveBeenCalledTimes(1);
    expect(mounted.container.textContent).not.toContain('Your Decks');
    expect(mounted.container.textContent).toContain('Public Control');
    expect(mounted.container.textContent).toContain('Start Playtest');

    mounted.unmount();
  });
});

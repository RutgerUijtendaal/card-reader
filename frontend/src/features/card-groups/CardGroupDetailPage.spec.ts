/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, type PropType } from 'vue';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardGroupDetailPage from '@/features/card-groups/CardGroupDetailPage.vue';
import type { CardDeckReferenceSummary } from '@/domain/card-deck-references/types';
import type { CardFiltersResponse, CardVersionDetail } from '@/domain/cards/types';
import type { CardGroupDetail } from '@/features/card-groups/types';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('@/shared/api/client', () => ({
  api: {
    get: apiGet,
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/domain/cards/components/CardVersionOverviewPane.vue', () => ({
  default: defineComponent({
    props: {
      version: {
        type: Object as PropType<CardVersionDetail>,
        required: true,
      },
    },
    setup(props) {
      return () => h('section', { 'data-testid': 'card-version-overview' }, props.version.name);
    },
  }),
}));

vi.mock('@/domain/cards/components/CardResultPager.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('nav', { 'data-testid': 'card-result-pager' }, 'Pager');
    },
  }),
}));

vi.mock('@/domain/card-deck-references/components/CardDeckReferencesPanel.vue', () => ({
  default: defineComponent({
    props: {
      deckReferences: {
        type: Array as PropType<CardDeckReferenceSummary[]>,
        required: true,
      },
      sourceCardId: {
        type: String,
        required: true,
      },
    },
    setup(props) {
      return () => h(
        'aside',
        {
          'data-testid': 'card-deck-references',
          'data-source-card-id': props.sourceCardId,
        },
        `Deck references: ${props.deckReferences.length}`,
      );
    },
  }),
}));

const buildCard = (id: string, name: string): CardVersionDetail => ({
  id,
  key: id,
  label: name,
  card_pool: 'player' as const, card_roles: [],
  deck_building_config: {},
  lifecycle_status: 'active',
  template_id: 'template-1',
  version_id: `${id}-version`,
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  content_version: null,
  name,
  type_line: 'Base Type',
  mana_cost: '2',
  mana_symbols: [],
  mana_value: 2,
  attack: null,
  health: null,
  rules_text: 'Base rules',
  rules_text_enriched: 'Base rules',
  confidence: 0.9,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  image_url: null,
  editable: true,
  keyword_ids: [],
  tag_ids: [],
  symbol_ids: [],
  type_ids: [],
  field_sources: {
    fields: {
      name: 'auto',
      type_line: 'auto',
      mana_cost: 'auto',
      attack: 'auto',
      health: 'auto',
      rules_text: 'auto',
    },
    metadata: {
      keywords: 'auto',
      tags: 'auto',
      types: 'auto',
      symbols: 'auto',
    },
  },
  parsed_snapshot: {
    fields: {
      name,
      type_line: 'Base Type',
      mana_cost: '2',
      attack: null,
      health: null,
      rules_text: 'Base rules',
    },
    metadata: {
      keyword_ids: [],
      tag_ids: [],
      type_ids: [],
      symbol_ids: [],
    },
  },
  parse_result: null,
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
});

const deckReference = {
  id: 'deck-1',
  card_reference: {
      as_hero: true,
    mainboard_quantity: 0,
    sideboard_quantity: 0,
  },
} as CardDeckReferenceSummary;

const buildGroup = (): CardGroupDetail => ({
  id: 'group-1',
  key: 'group-1',
  name: 'Group 1',
  anchor_card_id: 'card-1',
  anchor_deck_references: [],
  member_count: 2,
  members: [
    {
      position: 1,
      is_anchor: true,
      card: buildCard('card-1', 'Anchor Card'),
    },
    {
      position: 2,
      is_anchor: false,
      card: buildCard('card-2', 'Member Card'),
    },
  ],
});

const filters: CardFiltersResponse = {
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

const mountView = async (path: string, options: { flush?: boolean } = {}) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/cards', component: { template: '<div />' } },
      { path: '/cards/:id', component: { template: '<div />' } },
      { path: '/card-groups/:id', component: CardGroupDetailPage },
    ],
  });
  await router.push(path);
  await router.isReady();

  const app = createApp(CardGroupDetailPage);
  app.use(router);
  app.use(createPinia());
  app.mount(container);
  if (options.flush ?? true) {
    await flushPromises();
  }
  await nextTick();

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('CardGroupDetailPage', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('passes lifecycle query through to group detail request', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url === '/card-groups/group-1') {
        return Promise.resolve({ data: buildGroup() });
      }
      if (url === '/cards/filters') {
        return Promise.resolve({ data: filters });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    const mounted = await mountView('/card-groups/group-1?lifecycle_status=all');

    expect(apiGet).toHaveBeenCalledWith('/card-groups/group-1', {
      params: { lifecycle_status: 'all' },
    });

    mounted.unmount();
  });

  test('passes the Evil pool through to group detail request', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url === '/card-groups/group-1') {
        return Promise.resolve({ data: buildGroup() });
      }
      if (url === '/cards/filters') {
        return Promise.resolve({ data: filters });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    const mounted = await mountView('/card-groups/group-1?card_pool=evil');

    expect(apiGet).toHaveBeenCalledWith('/card-groups/group-1', {
      params: { card_pool: 'evil' },
    });

    mounted.unmount();
  });

  test('omits lifecycle query for default active group detail request', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url === '/card-groups/group-1') {
        return Promise.resolve({ data: buildGroup() });
      }
      if (url === '/cards/filters') {
        return Promise.resolve({ data: filters });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    const mounted = await mountView('/card-groups/group-1');

    expect(apiGet).toHaveBeenCalledWith('/card-groups/group-1', undefined);

    mounted.unmount();
  });

  test('renders a layout-shaped skeleton while loading initial data', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url === '/card-groups/group-1') {
        return new Promise(() => {});
      }
      if (url === '/cards/filters') {
        return Promise.resolve({ data: filters });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    const mounted = await mountView('/card-groups/group-1', { flush: false });

    expect(mounted.container.querySelector('[aria-label="Loading card group detail"]')).not.toBeNull();
    expect(mounted.container.textContent).not.toContain('Anchor Card');

    mounted.unmount();
  });

  test('renders group members vertically with anchor deck references', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url === '/card-groups/group-1') {
        return Promise.resolve({
          data: {
            ...buildGroup(),
            anchor_deck_references: [deckReference],
          },
        });
      }
      if (url === '/cards/filters') {
        return Promise.resolve({ data: filters });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    const mounted = await mountView('/card-groups/group-1');

    const overviews = Array.from(mounted.container.querySelectorAll('[data-testid="card-version-overview"]'));
    expect(overviews).toHaveLength(2);
    expect(overviews.map((element) => element.textContent)).toEqual(['Anchor Card', 'Member Card']);
    expect(mounted.container.textContent).toContain('Anchor');
    expect(mounted.container.textContent).toContain('Open card');
    const deckPanel = mounted.container.querySelector('[data-testid="card-deck-references"]');
    expect(deckPanel?.textContent).toBe('Deck references: 1');
    expect(deckPanel?.getAttribute('data-source-card-id')).toBe('card-1');

    mounted.unmount();
  });

  test('labels cross-pool members and keeps the originating workspace in their links', async () => {
    const group = buildGroup();
    group.members[1] = {
      ...group.members[1],
      card: { ...group.members[1].card, card_pool: 'evil' },
    };
    apiGet.mockImplementation((url: string) => {
      if (url === '/card-groups/group-1') {
        return Promise.resolve({ data: group });
      }
      if (url === '/cards/filters') {
        return Promise.resolve({ data: filters });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    const mounted = await mountView('/card-groups/group-1');
    const openLinks = Array.from(mounted.container.querySelectorAll<HTMLAnchorElement>('a'))
      .filter((link) => link.textContent?.trim() === 'Open card');

    expect(mounted.container.textContent).toContain('Evil');
    expect(openLinks[1]?.getAttribute('href')).toBe(
      '/cards/card-2?return_card_pool=player&card_pool=evil',
    );
    mounted.unmount();
  });
});

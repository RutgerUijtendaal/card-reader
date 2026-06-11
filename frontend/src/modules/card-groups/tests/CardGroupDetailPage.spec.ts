/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, type PropType } from 'vue';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardGroupDetailPage from '@/modules/card-groups/CardGroupDetailPage.vue';
import type { CardDeckReferenceSummary, CardFiltersResponse, CardGroupDetail, CardVersionDetail } from '@/modules/card-detail/types';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  api: {
    get: apiGet,
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/components/cards/CardVersionOverviewPane.vue', () => ({
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

vi.mock('@/components/cards/CardResultPager.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('nav', { 'data-testid': 'card-result-pager' }, 'Pager');
    },
  }),
}));

vi.mock('@/components/cards/CardDeckReferencesPanel.vue', () => ({
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
  is_hero: false,
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
    is_hero: true,
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
});

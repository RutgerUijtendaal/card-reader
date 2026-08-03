import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import NotificationCardVersionComparison from '@/modules/notifications/components/NotificationCardVersionComparison.vue';
import type { CardVersionDetail } from '@/modules/card-detail/types';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  api: { get: apiGet },
  toAbsoluteApiUrl: (url: string) => url,
}));

const buildVersion = (overrides: Partial<CardVersionDetail> = {}): CardVersionDetail => ({
  id: 'card-1',
  key: 'card-1',
  label: 'Changed Card',
  is_hero: false,
  deck_building_config: { overrides: {} },
  template_id: 'template-1',
  version_id: 'version-1',
  version_number: 1,
  previous_version_id: null,
  is_latest: false,
  editable: true,
  name: 'Changed Card',
  image_url: '/cards/card-1/versions/version-1/image',
  mana_cost: '1',
  mana_symbols: [],
  mana_value: 1,
  attack: null,
  health: null,
  type_line: 'Item',
  rules_text: '',
  rules_text_enriched: '',
  confidence: 1,
  created_at: '2026-06-07T10:00:00Z',
  updated_at: '2026-06-07T10:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
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
      name: 'Changed Card',
      type_line: 'Item',
      mana_cost: '1',
      attack: null,
      health: null,
      rules_text: '',
    },
    metadata: {
      keyword_ids: [],
      tag_ids: [],
      type_ids: [],
      symbol_ids: [],
    },
  },
  parse_result: null,
  ...overrides,
});

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

describe('NotificationCardVersionComparison', () => {
  afterEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    document.body.innerHTML = '';
  });

  test('loads and labels the exact before and after versions', async () => {
    localStorage.setItem('card-reader.gallery-options', JSON.stringify({ cardScale: 1.2 }));
    apiGet.mockResolvedValue({
      data: [
        buildVersion(),
        buildVersion({
          version_id: 'version-2',
          version_number: 2,
          previous_version_id: 'version-1',
          is_latest: true,
          image_url: '/cards/card-1/versions/version-2/image',
        }),
      ],
    });
    const openedVersions: string[] = [];
    const container = document.createElement('div');
    document.body.appendChild(container);
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div />' } }],
    });
    await router.push('/');
    await router.isReady();
    const app = createApp(
      defineComponent({
        setup() {
          return () => h(NotificationCardVersionComparison, {
            comparison: {
              cardId: 'card-1',
              beforeVersionId: 'version-1',
              afterVersionId: 'version-2',
            },
            onOpenCard: (versionId: string) => openedVersions.push(versionId),
          });
        },
      }),
    );
    app.use(router);
    app.mount(container);
    await flushPromises();
    await nextTick();

    expect(apiGet).toHaveBeenCalledWith('/cards/card-1/generations');
    expect(container.textContent).toContain('Version change');
    expect(container.textContent).toContain('Before');
    expect(container.textContent).toContain('Printing 1');
    expect(container.textContent).toContain('After');
    expect(container.textContent).toContain('Printing 2');
    expect(container.querySelector('[data-testid="version-change-arrow"]')).not.toBeNull();

    const cards = container.querySelectorAll<HTMLButtonElement>('button');
    expect(cards).toHaveLength(2);
    expect(cards[0]?.parentElement?.style.width).toBe('23.195rem');
    cards[0]?.click();
    cards[1]?.click();
    expect(openedVersions).toEqual(['version-1', 'version-2']);

    app.unmount();
    container.remove();
  });
});

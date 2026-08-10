import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardGroupsAdminView from '@/features/admin/views/CardGroupsAdminView.vue';
import type { CardGroupRecord } from '@/features/admin/types';
import type { CardListItem } from '@/domain/cards/types';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('@/shared/api/client', () => ({
  api: {
    get: apiGet,
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const buildCard = (
  cardPool: CardListItem['card_pool'] = 'player',
  cardId = 'card-1',
): CardListItem => ({
  id: cardId,
  key: cardId,
  result_type: 'card',
  image_url: '/card.png',
  label: 'Card 1',
  card_pool: cardPool, card_roles: [],
  template_id: 'template-1',
  version_id: 'version-1',
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name: 'Card 1',
  mana_cost: '1',
  mana_symbols: [],
  mana_value: 1,
  attack: null,
  health: null,
  type_line: 'Item',
  rules_text: '',
  confidence: 1,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
});

const buildGroup = (
  cardPool: CardGroupRecord['card_pool'] = 'player',
  withAnchor = false,
): CardGroupRecord => ({
  id: 'group-1',
  key: 'group-1',
  name: 'Group 1',
  card_pool: cardPool,
  anchor_card_id: withAnchor ? 'anchor-card' : '',
  anchor_card_name: withAnchor ? 'Anchor Card' : 'No anchor',
  member_count: withAnchor ? 1 : 0,
  members: withAnchor
    ? [{
        card_id: 'anchor-card',
        card_label: 'Anchor Card',
        card_name: 'Anchor Card',
        card_pool: cardPool,
        position: 1,
        is_anchor: true,
        image_url: '/anchor.png',
      }]
    : [],
});

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

const mountView = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div />' } }],
  });
  await router.push('/');
  await router.isReady();

  const app = createApp(CardGroupsAdminView);
  app.use(router);
  app.mount(container);
  await flushPromises();
  await nextTick();

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('CardGroupsAdminView', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('adds a cross-pool card and keeps the result visible as added', async () => {
    vi.useFakeTimers();
    apiGet.mockImplementation((url: string) => {
      if (url === '/admin/card-groups') {
        return Promise.resolve({ data: [buildGroup('game_master', true)] });
      }
      if (url === '/cards') {
        return Promise.resolve({
          data: {
            count: 1,
            next_page: null,
            previous_page: null,
            page: 1,
            page_size: 10,
            results: [buildCard('player', 'player-card')],
          },
        });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    const mounted = await mountView();
    const groupButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Group 1'),
    );
    if (!(groupButton instanceof HTMLButtonElement)) {
      throw new Error('expected group button');
    }
    groupButton.click();
    await nextTick();

    const poolSelect = mounted.container.querySelector<HTMLSelectElement>('select');
    if (!(poolSelect instanceof HTMLSelectElement)) {
      throw new Error('expected search pool select');
    }
    expect(poolSelect.value).toBe('game_master');
    poolSelect.value = 'player';
    poolSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();

    const searchInput = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Search cards to add..."]');
    if (!(searchInput instanceof HTMLInputElement)) {
      throw new Error('expected card search input');
    }
    searchInput.value = 'Card';
    searchInput.dispatchEvent(new Event('input', { bubbles: true }));
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    await nextTick();

    const addButton = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Add Card 1"]');
    if (!(addButton instanceof HTMLButtonElement)) {
      throw new Error('expected add card button');
    }
    addButton.click();
    await nextTick();

    expect(mounted.container.textContent).toContain('Position 2');
    expect(mounted.container.querySelector('button[aria-label="Added Card 1"]')).not.toBeNull();
    expect(apiGet).toHaveBeenCalledWith('/cards', {
      params: expect.objectContaining({
        q: 'Card',
        card_pool: 'player',
      }),
    });

    mounted.unmount();
  });

  test('disables card search until a group editor is active', async () => {
    vi.useFakeTimers();
    apiGet.mockImplementation((url: string) => {
      if (url === '/admin/card-groups') {
        return Promise.resolve({ data: [buildGroup()] });
      }
      if (url === '/cards') {
        return Promise.resolve({
          data: {
            count: 1,
            next_page: null,
            previous_page: null,
            page: 1,
            page_size: 10,
            results: [buildCard()],
          },
        });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    const mounted = await mountView();
    const searchInput = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Select or create a group first"]');
    if (!(searchInput instanceof HTMLInputElement)) {
      throw new Error('expected disabled card search input');
    }

    expect(searchInput.disabled).toBe(true);
    expect(mounted.container.textContent).toContain('Select or create a group before searching for cards.');

    searchInput.value = 'Card';
    searchInput.dispatchEvent(new Event('input', { bubbles: true }));
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    await nextTick();

    expect(apiGet).toHaveBeenCalledTimes(1);
    expect(apiGet).toHaveBeenCalledWith('/admin/card-groups');

    mounted.unmount();
  });
});

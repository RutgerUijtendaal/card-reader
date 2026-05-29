import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardMergesAdminView from '@/modules/admin/views/CardMergesAdminView.vue';
import type { CardMergePreview } from '@/modules/admin/types';
import type { CardListItem } from '@/modules/card-detail/types';

const { apiGet, apiPost } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  api: {
    get: apiGet,
    post: apiPost,
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const buildCard = (id: string, name: string): CardListItem => ({
  id,
  key: id,
  result_type: 'card',
  image_url: `/${id}.png`,
  label: name,
  is_hero: false,
  template_id: 'template-1',
  version_id: `${id}-version`,
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name,
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

const buildPreview = (): CardMergePreview => ({
  target: {
    id: 'target-1',
    key: 'target-1',
    label: 'Target Card',
    latest_name: 'Target Card',
    version_count: 1,
  },
  sources: [
    {
      id: 'source-1',
      key: 'source-1',
      label: 'Source Card',
      latest_name: 'Source Card',
      version_count: 1,
    },
  ],
  aliases: [],
  relations: {
    deck_entry_collisions: 0,
    sideboard_entry_collisions: 0,
    group_member_collisions: 0,
    hero_references: 0,
    anchored_groups: 0,
  },
  resulting_version_count: 2,
  blocking_conflicts: [],
  can_apply: true,
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
    routes: [{ path: '/admin', component: { template: '<div />' } }],
  });
  await router.push('/admin');
  await router.isReady();

  const app = createApp(CardMergesAdminView);
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

const searchAndSelect = async (
  input: HTMLInputElement,
  searchText: string,
  ariaLabel: string,
): Promise<void> => {
  input.focus();
  input.value = searchText;
  input.dispatchEvent(new Event('input', { bubbles: true }));
  await vi.advanceTimersByTimeAsync(300);
  await flushPromises();
  await nextTick();

  const resultButton = document.body.querySelector<HTMLButtonElement>(`button[aria-label="${ariaLabel}"]`);
  if (!(resultButton instanceof HTMLButtonElement)) {
    throw new Error(`expected result button ${ariaLabel}`);
  }
  resultButton.click();
  await nextTick();
};

describe('CardMergesAdminView', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('previews a single source card merged into a target card', async () => {
    vi.useFakeTimers();
    apiGet.mockImplementation((_url: string, config?: { params?: { q?: string } }) => {
      const query = config?.params?.q ?? '';
      const card = query.toLowerCase().includes('source')
        ? buildCard('source-1', 'Source Card')
        : buildCard('target-1', 'Target Card');
      return Promise.resolve({
        data: {
          count: 1,
          next_page: null,
          previous_page: null,
          page: 1,
          page_size: 12,
          results: [card],
        },
      });
    });
    apiPost.mockResolvedValue({ data: buildPreview() });

    const mounted = await mountView();
    const sourceInput = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Search duplicate card"]');
    const targetInput = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Search canonical card"]');
    if (!(sourceInput instanceof HTMLInputElement) || !(targetInput instanceof HTMLInputElement)) {
      throw new Error('expected merge search inputs');
    }

    await searchAndSelect(sourceInput, 'Source', 'Select Source Card');
    await searchAndSelect(targetInput, 'Target', 'Select Target Card');

    const previewButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Preview Merge'),
    );
    if (!(previewButton instanceof HTMLButtonElement)) {
      throw new Error('expected preview button');
    }
    previewButton.click();
    await flushPromises();
    await nextTick();

    expect(apiPost).toHaveBeenCalledWith('/admin/card-merges/preview', {
      target_card_id: 'target-1',
      source_card_ids: ['source-1'],
    });

    mounted.unmount();
  });
});

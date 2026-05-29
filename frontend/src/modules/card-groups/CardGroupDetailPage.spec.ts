import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardGroupDetailPage from '@/modules/card-groups/CardGroupDetailPage.vue';
import type { CardFiltersResponse, CardGroupDetail } from '@/modules/card-detail/types';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  api: {
    get: apiGet,
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/modules/card-detail/components/CardVersionPreviewPane.vue', () => ({
  default: {
    name: 'CardVersionPreviewPane',
    template: '<div />',
  },
}));

const buildGroup = (): CardGroupDetail => ({
  id: 'group-1',
  key: 'group-1',
  name: 'Group 1',
  anchor_card_id: 'card-1',
  member_count: 0,
  members: [],
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

const mountView = async (path: string) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/card-groups/:id', component: CardGroupDetailPage }],
  });
  await router.push(path);
  await router.isReady();

  const app = createApp(CardGroupDetailPage);
  app.use(router);
  app.mount(container);
  await flushPromises();
  await nextTick();

  return {
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
});

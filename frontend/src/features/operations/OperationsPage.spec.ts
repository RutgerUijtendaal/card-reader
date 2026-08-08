import { createApp } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { fetchOperationsOverview } from '@/features/operations/api';
import OperationsPage from '@/features/operations/OperationsPage.vue';
import type { OperationsOverview } from '@/features/operations/types';

vi.mock('@/features/operations/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/features/operations/api')>();
  return {
    ...original,
    fetchOperationsOverview: vi.fn(),
  };
});

const mockedFetchOperationsOverview = vi.mocked(fetchOperationsOverview);

const overview: OperationsOverview = {
  generated_at: '2026-08-08T03:00:00Z',
  stale_after_seconds: 30,
  workers: [],
  queues: [
    {
      key: 'imports',
      display_name: 'Card imports',
      worker_key: 'parser',
      total_count: 0,
      status_counts: {
        scheduled: 0,
        queued: 0,
        running: 0,
        canceling: 0,
        retrying: 0,
        completed: 0,
        failed: 0,
        cancelled: 0,
      },
      items: [],
    },
  ],
};

describe('OperationsPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  test('scrolls to a queue hash after the overview renders', async () => {
    mockedFetchOperationsOverview.mockResolvedValueOnce(overview);
    const scrollIntoView = vi.fn();
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    });
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/operations', component: OperationsPage }],
    });
    await router.push('/operations#queue-imports');
    await router.isReady();
    const container = document.createElement('div');
    document.body.appendChild(container);
    const app = createApp(OperationsPage);
    app.use(router);
    app.mount(container);

    await vi.waitFor(() => {
      expect(document.getElementById('queue-imports')).not.toBeNull();
      expect(scrollIntoView).toHaveBeenCalledWith({ block: 'start' });
    });

    app.unmount();
  });
});

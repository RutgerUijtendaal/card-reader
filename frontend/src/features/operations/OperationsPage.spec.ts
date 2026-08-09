import { createApp } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { fetchOperationsOverview, fetchOperationsQueuePage } from '@/features/operations/api';
import OperationsPage from '@/features/operations/OperationsPage.vue';
import type { OperationsOverview, OperationsQueuePage } from '@/features/operations/types';

vi.mock('@/features/operations/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/features/operations/api')>();
  return {
    ...original,
    fetchOperationsOverview: vi.fn(),
    fetchOperationsQueuePage: vi.fn(),
  };
});

const mockedFetchOperationsOverview = vi.mocked(fetchOperationsOverview);
const mockedFetchOperationsQueuePage = vi.mocked(fetchOperationsQueuePage);

const emptyPage: OperationsQueuePage = {
  count: 0,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 20,
  results: [],
};

const historyPage: OperationsQueuePage = {
  count: 1,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 20,
  results: [
    {
      id: 'sheet-1',
      title: 'Card sheet 1',
      status: 'running',
      native_status: 'rendering',
      created_at: '2026-08-08T02:00:00Z',
      updated_at: '2026-08-08T03:00:00Z',
      started_at: '2026-08-08T02:30:00Z',
      finished_at: null,
      progress_current: 4,
      progress_total: 10,
      error_message: null,
      metadata: [],
      links: [],
    },
  ],
};

const overview: OperationsOverview = {
  generated_at: '2026-08-08T03:00:00Z',
  stale_after_seconds: 30,
  workers: [
    {
      key: 'parser',
      display_name: 'Parser worker',
      queue_key: 'imports',
      health: 'online',
      activity: 'idle',
      active_instances: 1,
      last_seen_at: '2026-08-08T03:00:00Z',
      current_work_ids: [],
      instances: [],
    },
    {
      key: 'tts-sheet-renderer',
      display_name: 'TTS renderer',
      queue_key: 'tts-card-sheets',
      health: 'online',
      activity: 'busy',
      active_instances: 1,
      last_seen_at: '2026-08-08T03:00:00Z',
      current_work_ids: ['sheet-1'],
      instances: [],
    },
  ],
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
    {
      key: 'tts-card-sheets',
      display_name: 'TTS card sheets',
      worker_key: 'tts-sheet-renderer',
      total_count: 1,
      status_counts: {
        scheduled: 0,
        queued: 0,
        running: 1,
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

const mountPage = async (location: string, initialPage = emptyPage) => {
  mockedFetchOperationsOverview.mockResolvedValue(overview);
  mockedFetchOperationsQueuePage.mockImplementation(async (_queueKey, page, pageSize) => ({
    ...initialPage,
    page,
    page_size: pageSize,
    previous_page: page > 1 ? page - 1 : null,
  }));
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/operations', component: OperationsPage }],
  });
  await router.push(location);
  await router.isReady();
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(OperationsPage);
  app.use(router);
  app.mount(container);
  return { app, container, router };
};

describe('OperationsPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  test('preserves an inbound queue hash and requested history page', async () => {
    const mounted = await mountPage('/operations?page=2#queue-imports');

    await vi.waitFor(() => {
      expect(document.getElementById('queue-imports')).not.toBeNull();
      expect(mockedFetchOperationsQueuePage).toHaveBeenCalledWith('imports', 2, 20);
      expect(mounted.router.currentRoute.value.hash).toBe('#queue-imports');
    });

    mounted.app.unmount();
  });

  test('selects the first queue needing attention when no hash is provided', async () => {
    const mounted = await mountPage('/operations');

    await vi.waitFor(() => {
      expect(document.getElementById('queue-tts-card-sheets')).not.toBeNull();
      expect(mounted.router.currentRoute.value.hash).toBe('#queue-tts-card-sheets');
      expect(mockedFetchOperationsQueuePage).toHaveBeenCalledWith('tts-card-sheets', 1, 20);
    });
    const selectedQueueButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('TTS card sheets'),
    );
    expect(selectedQueueButton?.getAttribute('aria-current')).toBe('page');
    expect(selectedQueueButton?.classList.contains('rounded-lg')).toBe(true);
    expect(selectedQueueButton?.textContent).toContain('running 1');

    mounted.app.unmount();
  });

  test('keeps existing history visible when a manual refresh fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const mounted = await mountPage('/operations#queue-tts-card-sheets', historyPage);

    await vi.waitFor(() => {
      expect(mounted.container.textContent).toContain('Card sheet 1');
    });
    mockedFetchOperationsQueuePage.mockRejectedValueOnce(new Error('History unavailable'));

    const refreshButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Refresh',
    );
    refreshButton?.click();

    await vi.waitFor(() => {
      expect(mounted.container.textContent).toContain('Queue history could not be loaded.');
      expect(mounted.container.textContent).toContain('Card sheet 1');
    });
    expect(consoleError).toHaveBeenCalled();

    mounted.app.unmount();
  });
});

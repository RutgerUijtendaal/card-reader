import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { OperationsQueueItem } from '@/domain/operations/types';
import ImportActivityPanel from '@/features/import-jobs/components/ImportActivityPanel.vue';
import type { ImportJob } from '@/features/import-jobs/types';

const activeJob: ImportJob = {
  id: 'active-job',
  source_path: 'uploads/active-job',
  template_id: 'mtg-like-v1',
  content_version: null,
  status: 'running',
  total_items: 10,
  processed_items: 4,
  created_at: '2026-08-09T10:00:00Z',
  updated_at: '2026-08-09T10:01:00Z',
};

const recentJob: OperationsQueueItem = {
  id: 'finished-job',
  title: 'Default card · 16.2.0',
  status: 'completed',
  native_status: 'completed',
  created_at: '2026-08-09T09:00:00Z',
  updated_at: '2026-08-09T09:05:00Z',
  started_at: null,
  finished_at: null,
  progress_current: 10,
  progress_total: 10,
  error_message: null,
  metadata: [{ label: 'Source', value: 'uploads/finished-job' }],
  links: [],
};

const mountPanel = async (
  options: {
    activeJobs?: ImportJob[];
    recentJobs?: OperationsQueueItem[];
    activeLoaded?: boolean;
    historyLoaded?: boolean;
  } = {},
) => {
  const onRefresh = vi.fn();
  const onCancel = vi.fn();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/operations', component: { template: '<div />' } }],
  });
  await router.push('/operations');
  await router.isReady();
  const host = document.createElement('div');
  document.body.appendChild(host);
  const app = createApp(ImportActivityPanel, {
    activeJobs: options.activeJobs ?? [activeJob],
    recentJobs: options.recentJobs ?? [recentJob],
    activeLoaded: options.activeLoaded ?? true,
    historyLoaded: options.historyLoaded ?? true,
    refreshing: false,
    errorMessage: '',
    queuedCount: 0,
    runningCount: 1,
    cancelingCount: 0,
    cancellingJobIds: new Set<string>(),
    lastRefreshedAt: '10:05:00',
    onRefresh,
    onCancel,
  });
  app.use(router);
  app.mount(host);
  return { app, host, onRefresh, onCancel };
};

describe('ImportActivityPanel', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('shows cancellable active work and compact recent history inline', async () => {
    const mounted = await mountPanel();

    expect(mounted.host.querySelector('aside')).toBeNull();
    expect(
      mounted.host
        .querySelector('[data-testid="import-activity-panel"]')
        ?.classList.contains('theme-card-frame'),
    ).toBe(false);
    expect(mounted.host.textContent).toContain('mtg-like-v1 · Unversioned');
    expect(mounted.host.textContent).toContain('Default card · 16.2.0');
    expect(mounted.host.textContent).not.toContain('uploads/finished-job');
    expect(
      mounted.host.querySelector('a[href="/operations#queue-imports"]')?.textContent,
    ).toContain('Full history');
    const actions = mounted.host.querySelector('[data-testid="import-activity-actions"]');
    expect(actions?.classList.contains('flex-nowrap')).toBe(true);
    expect(actions?.classList.contains('flex-wrap')).toBe(false);

    mounted.host.querySelector<HTMLButtonElement>('button[aria-label="Refresh import activity"]')?.click();
    Array.from(mounted.host.querySelectorAll('button'))
      .find((button) => button.textContent?.trim() === 'Interrupt')
      ?.click();
    await nextTick();

    expect(mounted.onRefresh).toHaveBeenCalledOnce();
    expect(mounted.onCancel).toHaveBeenCalledWith('active-job');

    mounted.app.unmount();
  });

  test('uses concise empty states without hiding history access', async () => {
    const mounted = await mountPanel({ activeJobs: [], recentJobs: [] });

    expect(mounted.host.textContent).toContain('No active imports.');
    expect(mounted.host.textContent).toContain('No recent import history.');
    expect(mounted.host.querySelector('a[href="/operations#queue-imports"]')).not.toBeNull();

    mounted.app.unmount();
  });

  test('shows active controls while recent history is still loading', async () => {
    const mounted = await mountPanel({ historyLoaded: false });

    expect(mounted.host.textContent).toContain('mtg-like-v1 · Unversioned');
    expect(mounted.host.textContent).toContain('Interrupt');
    expect(mounted.host.querySelector('[aria-label="Loading active imports"]')).toBeNull();
    expect(
      mounted.host.querySelector('[aria-label="Loading recent import history"]'),
    ).not.toBeNull();

    mounted.app.unmount();
  });
});

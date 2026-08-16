import { createApp, defineComponent, h } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { fetchOperationsQueuePage } from '@/domain/operations/api';
import type { OperationsQueueItem, OperationsQueuePage } from '@/domain/operations/types';
import { fetchTemplates } from '@/domain/templates/api';
import {
  cancelImportJob,
  createImportJob,
  fetchCurrentContentVersion,
  fetchImportJobs,
  fetchImportJobByCreationKey,
  fetchImportJobDetail,
} from '@/features/import-jobs/api';
import { useImportJobsController } from '@/features/import-jobs/composables/useImportJobsController';
import type { ContentVersion, ImportJob, ImportJobDetail } from '@/features/import-jobs/types';

vi.mock('@/domain/operations/api', () => ({
  fetchOperationsQueuePage: vi.fn(),
}));
vi.mock('@/domain/templates/api', () => ({
  fetchTemplates: vi.fn(),
}));
vi.mock('@/features/import-jobs/api', () => ({
  cancelImportJob: vi.fn(),
  createImportJob: vi.fn(),
  fetchCurrentContentVersion: vi.fn(),
  fetchImportJobs: vi.fn(),
  fetchImportJobByCreationKey: vi.fn(),
  fetchImportJobDetail: vi.fn(),
}));

const activeJob = (id = 'active-job'): ImportJob => ({
  id,
  source_path: `uploads/${id}`,
  template_id: 'mtg-like-v1',
  content_version: {
    id: 'version-1',
    version_number: '16.2.0',
    base_version: '16.2',
    description: 'Current release.',
  },
  status: 'running',
  total_items: 10,
  processed_items: 4,
  created_at: '2026-08-09T10:00:00Z',
  updated_at: '2026-08-09T10:01:00Z',
  card_pool: 'player',
  card_role_mode: 'automatic',
  card_role_override: [],
  card_faction_mode: 'automatic',
  card_faction_override: [],
  card_mana_family_mode: 'automatic',
  card_mana_family_override: [],
  classification_rule_snapshot: {
    schema_version: 1,
    card_pool: 'player',
    rules: [],
    digest: 'abc123',
  },
});

const importJobDetail = (id: string): ImportJobDetail => ({
  ...activeJob(id),
  items: [],
});

const historyItem = (id: string, status: OperationsQueueItem['status']): OperationsQueueItem => ({
  id,
  title: `Import ${id}`,
  status,
  native_status: status,
  created_at: '2026-08-09T09:00:00Z',
  updated_at: '2026-08-09T09:05:00Z',
  started_at: null,
  finished_at: null,
  progress_current: 10,
  progress_total: 10,
  error_message: null,
  metadata: [],
  links: [],
});

const historyPage = (
  results: OperationsQueueItem[],
  options: { page?: number; nextPage?: number | null; count?: number } = {},
): OperationsQueuePage => ({
  count: options.count ?? results.length,
  next_page: options.nextPage ?? null,
  previous_page: (options.page ?? 1) > 1 ? (options.page ?? 1) - 1 : null,
  page: options.page ?? 1,
  page_size: 100,
  results,
});

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
};

const currentVersion = {
  id: 'version-1',
  version_number: '16.2.0',
  base_version: '16.2',
  description: 'Current release.',
};

const mountController = () => {
  let controller!: ReturnType<typeof useImportJobsController>;
  const host = document.createElement('div');
  document.body.appendChild(host);
  const app = createApp(
    defineComponent({
      setup() {
        controller = useImportJobsController();
        return () => h('div');
      },
    }),
  );
  app.mount(host);
  return { app, controller };
};

describe('useImportJobsController', () => {
  beforeEach(() => {
    vi.mocked(fetchTemplates).mockResolvedValue([
      {
        id: 'template-1',
        key: 'mtg-like-v1',
        label: 'Default card',
        definition_json: '{}',
      },
    ]);
    vi.mocked(fetchCurrentContentVersion).mockResolvedValue(currentVersion);
    vi.mocked(fetchImportJobs).mockResolvedValue([activeJob()]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValue(
      historyPage([
        historyItem('active-job', 'running'),
        historyItem('finished-job', 'completed'),
      ]),
    );
    vi.mocked(createImportJob).mockResolvedValue({
      ...activeJob('created-job'),
      job_id: 'created-job',
      idempotent_replay: false,
    });
    vi.mocked(fetchImportJobByCreationKey).mockResolvedValue(null);
    vi.mocked(fetchImportJobDetail).mockResolvedValue(importJobDetail('detail-job'));
    vi.mocked(cancelImportJob).mockResolvedValue({
      ...activeJob(),
      status: 'canceling',
    });
  });

  test('leaves template and card pool unselected after form options load', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.formLoaded.value).toBe(true));

    expect(mounted.controller.templates.value).toHaveLength(1);
    expect(mounted.controller.pickerTemplateId.value).toBeNull();
    expect(mounted.controller.cardPool.value).toBeNull();
    mounted.app.unmount();
  });

  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('loads form options independently from active and recent activity', async () => {
    const mounted = mountController();

    await vi.waitFor(() => {
      expect(mounted.controller.formLoaded.value).toBe(true);
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });

    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['active-job']);
    expect(mounted.controller.recentJobs.value.map((job) => job.id)).toEqual(['finished-job']);
    expect(fetchOperationsQueuePage).toHaveBeenCalledWith('imports', 1, 100);

    mounted.app.unmount();
  });

  test('shows the form before a slow version prefill and preserves user input', async () => {
    const currentVersionRequest = deferred<ContentVersion>();
    vi.mocked(fetchCurrentContentVersion).mockImplementationOnce(
      () => currentVersionRequest.promise,
    );
    const mounted = mountController();

    await vi.waitFor(() => expect(mounted.controller.formLoaded.value).toBe(true));
    expect(mounted.controller.currentContentVersionLoaded.value).toBe(false);
    expect(mounted.controller.templates.value).toHaveLength(1);

    mounted.controller.contentVersionBase.value = '20.1';
    mounted.controller.contentVersionDescription.value = 'User-entered release.';
    currentVersionRequest.resolve(currentVersion);
    await vi.waitFor(() => {
      expect(mounted.controller.currentContentVersionLoaded.value).toBe(true);
    });

    expect(mounted.controller.currentContentVersion.value).toEqual(currentVersion);
    expect(mounted.controller.contentVersionBase.value).toBe('20.1');
    expect(mounted.controller.contentVersionDescription.value).toBe('User-entered release.');

    mounted.app.unmount();
  });

  test('keeps activity data when a manual refresh fails', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    vi.mocked(fetchImportJobs).mockRejectedValueOnce(new Error('Active unavailable'));
    vi.mocked(fetchOperationsQueuePage).mockRejectedValueOnce(new Error('History unavailable'));

    await mounted.controller.refreshActivity();

    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['active-job']);
    expect(mounted.controller.recentJobs.value.map((job) => job.id)).toEqual(['finished-job']);
    expect(mounted.controller.activityErrorMessage.value).toBe(
      'Import activity could not be refreshed.',
    );

    mounted.app.unmount();
  });

  test('does not overlap polling while the unified activity refresh is pending', async () => {
    const pendingHistoryRequest = deferred<OperationsQueuePage>();
    vi.mocked(fetchOperationsQueuePage).mockImplementationOnce(
      () => pendingHistoryRequest.promise,
    );
    const mounted = mountController();

    await vi.waitFor(() => expect(mounted.controller.activeJobsLoaded.value).toBe(true));
    expect(mounted.controller.historyLoaded.value).toBe(false);
    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['active-job']);

    vi.mocked(fetchImportJobs).mockResolvedValueOnce([activeJob()]);
    await mounted.controller.pollJobs();

    expect(fetchImportJobs).toHaveBeenCalledOnce();
    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['active-job']);

    pendingHistoryRequest.resolve(historyPage([historyItem('active-job', 'running')]));
    await vi.waitFor(() => expect(mounted.controller.historyLoaded.value).toBe(true));
    await mounted.controller.pollJobs();

    expect(fetchImportJobs).toHaveBeenCalledTimes(2);

    mounted.app.unmount();
  });

  test('ignores an older active-job response that resolves after a newer refresh', async () => {
    const initialActiveRequest = deferred<ImportJob[]>();
    vi.mocked(fetchImportJobs)
      .mockImplementationOnce(() => initialActiveRequest.promise)
      .mockResolvedValueOnce([activeJob('new-job')]);
    const mounted = mountController();
    await vi.waitFor(() => expect(fetchImportJobs).toHaveBeenCalledOnce());
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([historyItem('new-job', 'running')]),
    );

    await mounted.controller.refreshActivity();
    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['new-job']);

    initialActiveRequest.resolve([]);
    await Promise.resolve();
    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['new-job']);

    mounted.app.unmount();
  });

  test('pages through active history rows until five terminal jobs are available', async () => {
    const firstPageItems = Array.from(
      { length: 100 },
      (_, index) => historyItem(`running-${index}`, 'running'),
    );
    const terminalItems = Array.from(
      { length: 6 },
      (_, index) => historyItem(`finished-${index}`, 'completed'),
    );
    vi.mocked(fetchOperationsQueuePage).mockImplementation(async (_queue, page) => {
      if (page === 1) {
        return historyPage(firstPageItems, { nextPage: 2, count: 106 });
      }
      return historyPage(terminalItems, { page: 2, count: 106 });
    });
    const mounted = mountController();

    await vi.waitFor(() => expect(mounted.controller.historyLoaded.value).toBe(true));

    expect(fetchOperationsQueuePage).toHaveBeenNthCalledWith(1, 'imports', 1, 100);
    expect(fetchOperationsQueuePage).toHaveBeenNthCalledWith(2, 'imports', 2, 100);
    expect(mounted.controller.recentJobs.value.map((job) => job.id)).toEqual([
      'finished-0',
      'finished-1',
      'finished-2',
      'finished-3',
      'finished-4',
    ]);

    mounted.app.unmount();
  });

  test('reconciles history when concurrent activity snapshots miss a finished job', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });

    const activeSnapshot = deferred<ImportJob[]>();
    vi.mocked(fetchImportJobs).mockImplementationOnce(() => activeSnapshot.promise);
    vi.mocked(fetchOperationsQueuePage)
      .mockResolvedValueOnce(historyPage([historyItem('active-job', 'running')]))
      .mockResolvedValueOnce(historyPage([historyItem('active-job', 'completed')]));

    const refresh = mounted.controller.refreshActivity();
    await vi.waitFor(() => expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(2));
    activeSnapshot.resolve([]);
    await refresh;

    expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(3);
    expect(mounted.controller.activeJobs.value).toEqual([]);
    expect(mounted.controller.recentJobs.value.map((job) => job.id)).toEqual(['active-job']);

    mounted.app.unmount();
  });

  test('reloads active jobs when history observes newly queued work', async () => {
    vi.mocked(fetchImportJobs).mockResolvedValueOnce([]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(historyPage([]));
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });

    vi.mocked(fetchImportJobs)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([activeJob('new-job')]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([historyItem('new-job', 'running')]),
    );

    await mounted.controller.refreshActivity();

    expect(fetchImportJobs).toHaveBeenCalledTimes(3);
    expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(2);
    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['new-job']);

    mounted.app.unmount();
  });

  test('clears a history error only after the unified poll refresh succeeds', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });

    vi.mocked(fetchImportJobs).mockResolvedValueOnce([activeJob()]);
    vi.mocked(fetchOperationsQueuePage).mockRejectedValueOnce(new Error('History unavailable'));
    await mounted.controller.refreshActivity();
    expect(mounted.controller.activityErrorMessage.value).toBe(
      'Import activity could not be refreshed.',
    );

    vi.mocked(fetchImportJobs).mockResolvedValueOnce([activeJob()]);
    await mounted.controller.pollJobs();

    expect(mounted.controller.activityErrorMessage.value).toBe('');
    expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(3);

    mounted.app.unmount();
  });

  test('refreshes recent history when polling observes a finished active job', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    vi.mocked(fetchImportJobs).mockResolvedValueOnce([]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([historyItem('active-job', 'completed')]),
    );

    await mounted.controller.pollJobs();

    expect(mounted.controller.activeJobs.value).toEqual([]);
    expect(mounted.controller.recentJobs.value.map((job) => job.id)).toEqual(['active-job']);
    expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(2);

    mounted.app.unmount();
  });

  test('refreshes an open active-job detail through its terminal state', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    await mounted.controller.viewJobDetail('active-job');

    vi.mocked(fetchImportJobs).mockResolvedValueOnce([]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([historyItem('active-job', 'completed')]),
    );
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce({
      ...importJobDetail('active-job'),
      status: 'completed',
      processed_items: 10,
    });

    await mounted.controller.pollJobs();

    expect(fetchImportJobDetail).toHaveBeenCalledTimes(2);
    expect(mounted.controller.selectedJobDetail.value?.status).toBe('completed');
    expect(mounted.controller.selectedJobDetail.value?.processed_items).toBe(10);

    mounted.app.unmount();
  });

  test('refreshes the open detail when cancelling the last active job', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    await mounted.controller.viewJobDetail('active-job');

    vi.mocked(fetchImportJobs).mockResolvedValue([]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([historyItem('active-job', 'cancelled')]),
    );
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce({
      ...importJobDetail('active-job'),
      status: 'cancelled',
    });

    await mounted.controller.cancelJob('active-job');

    expect(cancelImportJob).toHaveBeenCalledWith('active-job');
    expect(mounted.controller.activeJobs.value).toEqual([]);
    expect(mounted.controller.selectedJobDetail.value?.status).toBe('cancelled');

    mounted.app.unmount();
  });

  test('keeps cancellation authoritative when every follow-up read fails', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce(importJobDetail('active-job'));
    await mounted.controller.viewJobDetail('active-job');
    vi.mocked(fetchImportJobs).mockRejectedValueOnce(new Error('Active unavailable'));
    vi.mocked(fetchOperationsQueuePage).mockRejectedValueOnce(new Error('History unavailable'));
    vi.mocked(fetchImportJobDetail).mockRejectedValueOnce(new Error('Detail unavailable'));

    await mounted.controller.cancelJob('active-job');

    expect(cancelImportJob).toHaveBeenCalledWith('active-job');
    expect(mounted.controller.activeJobs.value[0]?.status).toBe('canceling');
    expect(mounted.controller.selectedJobDetail.value?.status).toBe('canceling');
    expect(mounted.controller.activityErrorMessage.value).toBe(
      'Import activity could not be refreshed.',
    );
    mounted.app.unmount();
  });

  test('preserves a queued cancellation terminal response when refresh fails', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    mounted.controller.activeJobs.value = [
      { ...activeJob('queued-job'), status: 'queued' },
    ];
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce({
      ...importJobDetail('queued-job'),
      status: 'queued',
    });
    await mounted.controller.viewJobDetail('queued-job');
    vi.mocked(cancelImportJob).mockResolvedValueOnce({
      ...activeJob('queued-job'),
      status: 'cancelled',
      processed_items: 10,
    });
    vi.mocked(fetchImportJobDetail).mockRejectedValueOnce(new Error('Detail unavailable'));
    vi.mocked(fetchImportJobs).mockRejectedValueOnce(new Error('Active unavailable'));
    vi.mocked(fetchOperationsQueuePage).mockRejectedValueOnce(new Error('History unavailable'));

    await mounted.controller.cancelJob('queued-job');

    expect(mounted.controller.activeJobs.value).toEqual([]);
    expect(mounted.controller.selectedJobDetail.value?.status).toBe('cancelled');
    mounted.app.unmount();
  });

  test('refreshes queued item states after a terminal cancellation response', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    mounted.controller.activeJobs.value = [
      { ...activeJob('queued-job'), status: 'queued' },
    ];
    const queuedItem = {
      id: 'queued-item',
      source_file: 'queued.png',
      status: 'queued' as const,
      error_message: null,
      warning_code: null,
      warning_message: null,
      warnings: [],
      resolved_card_roles: [],
      resolved_card_factions: [],
      resolved_card_mana_families: [],
      classification_inference: {},
      target_card_id: null,
      target_card_version_id: null,
      target_card_pool_snapshot: null,
      target_card_roles_snapshot: [],
      target_card_factions_snapshot: [],
      target_card_mana_families_snapshot: [],
      card_tab_url: null,
    };
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce({
      ...importJobDetail('queued-job'),
      status: 'queued',
      items: [queuedItem],
    });
    await mounted.controller.viewJobDetail('queued-job');
    vi.mocked(cancelImportJob).mockResolvedValueOnce({
      ...activeJob('queued-job'),
      status: 'cancelled',
      processed_items: 10,
    });
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce({
      ...importJobDetail('queued-job'),
      status: 'cancelled',
      processed_items: 10,
      items: [{ ...queuedItem, status: 'cancelled' }],
    });
    vi.mocked(fetchImportJobs).mockResolvedValueOnce([]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([historyItem('queued-job', 'cancelled')]),
    );

    await mounted.controller.cancelJob('queued-job');

    expect(fetchImportJobDetail).toHaveBeenCalledTimes(2);
    expect(mounted.controller.selectedJobDetail.value?.status).toBe('cancelled');
    expect(mounted.controller.selectedJobDetail.value?.items[0]?.status).toBe('cancelled');
    mounted.app.unmount();
  });

  test('reconciles a terminal cancellation while the selected detail request is pending', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    mounted.controller.activeJobs.value = [
      { ...activeJob('queued-job'), status: 'queued' },
    ];
    const pendingDetail = deferred<ImportJobDetail>();
    vi.mocked(fetchImportJobDetail).mockImplementationOnce(() => pendingDetail.promise);
    const viewPromise = mounted.controller.viewJobDetail('queued-job');
    await vi.waitFor(() => expect(fetchImportJobDetail).toHaveBeenCalledOnce());
    vi.mocked(cancelImportJob).mockResolvedValueOnce({
      ...activeJob('queued-job'),
      status: 'cancelled',
      processed_items: 10,
    });
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce({
      ...importJobDetail('queued-job'),
      status: 'cancelled',
      processed_items: 10,
    });
    vi.mocked(fetchImportJobs).mockResolvedValueOnce([]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([historyItem('queued-job', 'cancelled')]),
    );

    await mounted.controller.cancelJob('queued-job');
    pendingDetail.reject(new Error('Stale detail request failed'));
    await viewPromise;

    expect(fetchImportJobDetail).toHaveBeenCalledTimes(2);
    expect(mounted.controller.selectedJobDetail.value?.status).toBe('cancelled');
    mounted.app.unmount();
  });

  test('invalidates a pending selected detail request when cancellation is still in progress', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    mounted.controller.activeJobs.value = [
      { ...activeJob('running-job'), status: 'running' },
    ];
    const pendingDetail = deferred<ImportJobDetail>();
    vi.mocked(fetchImportJobDetail).mockImplementationOnce(() => pendingDetail.promise);
    const viewPromise = mounted.controller.viewJobDetail('running-job');
    await vi.waitFor(() => expect(fetchImportJobDetail).toHaveBeenCalledOnce());
    vi.mocked(cancelImportJob).mockResolvedValueOnce({
      ...activeJob('running-job'),
      status: 'canceling',
    });
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce({
      ...importJobDetail('running-job'),
      status: 'running',
    });
    vi.mocked(fetchImportJobs).mockResolvedValueOnce([
      { ...activeJob('running-job'), status: 'canceling' },
    ]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(historyPage([]));

    await mounted.controller.cancelJob('running-job');
    pendingDetail.resolve({
      ...importJobDetail('running-job'),
      status: 'running',
    });
    await viewPromise;

    expect(mounted.controller.selectedJobDetail.value?.status).toBe('canceling');
    mounted.app.unmount();
  });

  test('clears a stale cancellation error after activity refresh succeeds', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    vi.mocked(cancelImportJob).mockRejectedValueOnce(new Error('Cancellation unavailable'));

    await mounted.controller.cancelJob('active-job');
    expect(mounted.controller.activityErrorMessage.value).toBe('Cancellation unavailable');

    await mounted.controller.refreshActivity();

    expect(mounted.controller.activityErrorMessage.value).toBe('');
    mounted.app.unmount();
  });

  test('reconciles unseen active work discovered by polling history', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });

    vi.mocked(fetchImportJobs)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([activeJob('new-job')]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([
        historyItem('active-job', 'completed'),
        historyItem('new-job', 'running'),
      ]),
    );

    await mounted.controller.pollJobs();

    expect(fetchImportJobs).toHaveBeenCalledTimes(3);
    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['new-job']);
    expect(mounted.controller.recentJobs.value.map((job) => job.id)).toEqual(['active-job']);

    mounted.app.unmount();
  });

  test('requires explicit card setup, submits it, and clears it after success', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.formLoaded.value).toBe(true));
    const file = new File(['image'], 'card.png', { type: 'image/png' });
    mounted.controller.pickedFiles.value = [file];
    const initialInputKey = mounted.controller.fileInputKey.value;
    const initialCreationKey = mounted.controller.creationKey.value;

    await mounted.controller.createJobFromPicker();
    expect(mounted.controller.formErrorMessage.value).toBe('Please select a template.');
    expect(createImportJob).not.toHaveBeenCalled();

    mounted.controller.pickerTemplateId.value = 'mtg-like-v1';
    await mounted.controller.createJobFromPicker();
    expect(mounted.controller.formErrorMessage.value).toBe('Please select a card pool.');
    expect(createImportJob).not.toHaveBeenCalled();

    mounted.controller.setCardPool('player');
    await mounted.controller.createJobFromPicker();

    expect(createImportJob).toHaveBeenCalledWith({
      creationKey: expect.any(String),
      templateId: 'mtg-like-v1',
      contentVersionBase: '16.2',
      contentVersionDescription: 'Current release.',
      files: [file],
      cardPool: 'player',
      cardRoleMode: 'automatic',
      cardRoleOverride: [],
      cardFactionMode: 'automatic',
      cardFactionOverride: [],
      cardManaFamilyMode: 'automatic',
      cardManaFamilyOverride: [],
    });
    expect(mounted.controller.pickedFiles.value).toEqual([]);
    expect(mounted.controller.fileInputKey.value).toBe(initialInputKey + 1);
    expect(mounted.controller.creationKey.value).not.toBe(initialCreationKey);
    expect(mounted.controller.pickerTemplateId.value).toBeNull();
    expect(mounted.controller.cardPool.value).toBeNull();
    expect(mounted.controller.cardRoleMode.value).toBe('automatic');
    expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(2);

    mounted.app.unmount();
  });

  test('locks an ambiguous attempt and retries the exact immutable payload', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.formLoaded.value).toBe(true));
    const file = new File(['image'], 'card.png', { type: 'image/png' });
    mounted.controller.pickedFiles.value = [file];
    mounted.controller.pickerTemplateId.value = 'mtg-like-v1';
    mounted.controller.cardPool.value = 'evil';
    mounted.controller.cardRoleMode.value = 'override';
    mounted.controller.cardRoleOverride.value = ['boon'];
    mounted.controller.cardFactionMode.value = 'override';
    mounted.controller.cardFactionOverride.value = ['blood'];
    mounted.controller.cardManaFamilyMode.value = 'override';
    mounted.controller.cardManaFamilyOverride.value = ['dark'];
    vi.mocked(createImportJob).mockRejectedValueOnce(new Error('connection lost'));
    vi.mocked(fetchImportJobByCreationKey).mockResolvedValueOnce(null);

    await mounted.controller.createJobFromPicker();

    expect(mounted.controller.createState.value.phase).toBe('uncertain');
    expect(mounted.controller.formLocked.value).toBe(true);
    const beforeUnload = new Event('beforeunload', { cancelable: true });
    expect(window.dispatchEvent(beforeUnload)).toBe(false);
    expect(beforeUnload.defaultPrevented).toBe(true);
    const firstPayload = vi.mocked(createImportJob).mock.calls[0][0];

    vi.mocked(createImportJob).mockResolvedValueOnce({
      ...activeJob('reconciled-job'),
      job_id: 'reconciled-job',
      idempotent_replay: true,
    });
    await mounted.controller.createJobFromPicker();

    expect(vi.mocked(createImportJob).mock.calls[1][0]).toBe(firstPayload);
    expect(mounted.controller.pickedFiles.value).toEqual([]);
    expect(mounted.controller.cardRoleMode.value).toBe('automatic');
    expect(mounted.controller.cardRoleOverride.value).toEqual([]);
    expect(mounted.controller.cardFactionMode.value).toBe('automatic');
    expect(mounted.controller.cardFactionOverride.value).toEqual([]);
    expect(mounted.controller.cardManaFamilyMode.value).toBe('automatic');
    expect(mounted.controller.cardManaFamilyOverride.value).toEqual([]);
    expect(mounted.controller.pickerTemplateId.value).toBeNull();
    expect(mounted.controller.cardPool.value).toBeNull();
    expect(window.dispatchEvent(new Event('beforeunload', { cancelable: true }))).toBe(true);

    mounted.app.unmount();
  });

  test('keeps only the latest requested import detail and loading state', async () => {
    const firstRequest = deferred<ImportJobDetail>();
    const secondRequest = deferred<ImportJobDetail>();
    vi.mocked(fetchImportJobDetail)
      .mockImplementationOnce(() => firstRequest.promise)
      .mockImplementationOnce(() => secondRequest.promise);
    const mounted = mountController();

    const firstLoad = mounted.controller.viewJobDetail('job-a');
    const secondLoad = mounted.controller.viewJobDetail('job-b');
    secondRequest.resolve(importJobDetail('job-b'));
    await secondLoad;

    expect(mounted.controller.selectedJobDetail.value?.id).toBe('job-b');
    expect(mounted.controller.detailLoading.value).toBe(false);

    firstRequest.resolve(importJobDetail('job-a'));
    await firstLoad;

    expect(mounted.controller.selectedJobDetail.value?.id).toBe('job-b');
    expect(mounted.controller.detailLoading.value).toBe(false);

    mounted.app.unmount();
  });

  test('manual detail selection wins over an overlapping background refresh', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.activeJobsLoaded.value).toBe(true));
    await mounted.controller.viewJobDetail('active-job');

    const background = deferred<ImportJobDetail>();
    const manual = deferred<ImportJobDetail>();
    vi.mocked(fetchImportJobDetail)
      .mockImplementationOnce(() => background.promise)
      .mockImplementationOnce(() => manual.promise);
    const refresh = mounted.controller.refreshActivity();
    await vi.waitFor(() => expect(fetchImportJobDetail).toHaveBeenCalledTimes(2));
    const selection = mounted.controller.viewJobDetail('manual-job');
    manual.resolve(importJobDetail('manual-job'));
    await selection;

    background.resolve(importJobDetail('active-job'));
    await refresh;

    expect(mounted.controller.selectedJobDetail.value?.id).toBe('manual-job');
    mounted.app.unmount();
  });

  test('closing detail while a request is in flight does not reopen it', async () => {
    const request = deferred<ImportJobDetail>();
    vi.mocked(fetchImportJobDetail).mockImplementationOnce(() => request.promise);
    const mounted = mountController();

    const selection = mounted.controller.viewJobDetail('active-job');
    mounted.controller.closeJobDetail();
    request.resolve(importJobDetail('active-job'));
    await selection;

    expect(mounted.controller.selectedJobDetail.value).toBeNull();
    expect(mounted.controller.detailLoading.value).toBe(false);
    mounted.app.unmount();
  });

  test('a detail refresh failure preserves successful list and history updates', async () => {
    const mounted = mountController();
    await vi.waitFor(() => {
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });
    await mounted.controller.viewJobDetail('active-job');
    vi.mocked(fetchImportJobs).mockResolvedValueOnce([activeJob('new-job')]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValueOnce(
      historyPage([
        historyItem('active-job', 'completed'),
        historyItem('new-job', 'running'),
        historyItem('new-finished', 'completed'),
      ]),
    );
    vi.mocked(fetchImportJobDetail).mockRejectedValueOnce(new Error('Detail unavailable'));

    await mounted.controller.refreshActivity();

    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['new-job']);
    expect(mounted.controller.recentJobs.value.map((job) => job.id)).toContain('new-finished');
    expect(mounted.controller.activityErrorMessage.value).toBe(
      'Import details could not be refreshed.',
    );
    mounted.app.unmount();
  });

  test('terminal details are not refreshed by later polling', async () => {
    vi.mocked(fetchImportJobDetail).mockResolvedValueOnce({
      ...importJobDetail('finished-job'),
      status: 'completed',
    });
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.activeJobsLoaded.value).toBe(true));
    await mounted.controller.viewJobDetail('finished-job');

    await mounted.controller.pollJobs();

    expect(fetchImportJobDetail).toHaveBeenCalledOnce();
    mounted.app.unmount();
  });

  test('keeps activity usable when form options fail to load', async () => {
    vi.mocked(fetchTemplates).mockRejectedValueOnce(new Error('Templates unavailable'));
    const mounted = mountController();

    await vi.waitFor(() => {
      expect(mounted.controller.formLoaded.value).toBe(true);
      expect(mounted.controller.activeJobsLoaded.value).toBe(true);
      expect(mounted.controller.historyLoaded.value).toBe(true);
    });

    expect(mounted.controller.formErrorMessage.value).toBe('Import options could not be loaded.');
    expect(mounted.controller.activeJobs.value).toHaveLength(1);

    mounted.app.unmount();
  });
});

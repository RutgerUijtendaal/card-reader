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
  template_role_snapshot: [],
  card_role_inference_policy_version: 1,
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
        inferred_card_roles: [],
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
    vi.mocked(cancelImportJob).mockResolvedValue();
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

  test('keeps active jobs usable and polling while recent history is pending', async () => {
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

    expect(fetchImportJobs).toHaveBeenCalledTimes(2);
    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['active-job']);

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

  test('preserves a history refresh failure after a successful active-only poll', async () => {
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

    expect(mounted.controller.activityErrorMessage.value).toBe(
      'Import activity could not be refreshed.',
    );
    expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(2);

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

  test('submits the existing import payload and resets the native picker key', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.formLoaded.value).toBe(true));
    const file = new File(['image'], 'card.png', { type: 'image/png' });
    mounted.controller.pickedFiles.value = [file];
    const initialInputKey = mounted.controller.fileInputKey.value;
    const initialCreationKey = mounted.controller.creationKey.value;

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
    });
    expect(mounted.controller.pickedFiles.value).toEqual([]);
    expect(mounted.controller.fileInputKey.value).toBe(initialInputKey + 1);
    expect(mounted.controller.creationKey.value).not.toBe(initialCreationKey);
    expect(mounted.controller.cardRoleMode.value).toBe('automatic');
    expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(2);

    mounted.app.unmount();
  });

  test('locks an ambiguous attempt and retries the exact immutable payload', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.formLoaded.value).toBe(true));
    const file = new File(['image'], 'card.png', { type: 'image/png' });
    mounted.controller.pickedFiles.value = [file];
    mounted.controller.cardPool.value = 'game_master';
    mounted.controller.cardRoleMode.value = 'override';
    mounted.controller.cardRoleOverride.value = ['boon'];
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

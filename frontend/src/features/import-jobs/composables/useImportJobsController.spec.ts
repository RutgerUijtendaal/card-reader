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
} from '@/features/import-jobs/api';
import { useImportJobsController } from '@/features/import-jobs/composables/useImportJobsController';
import type { ImportJob } from '@/features/import-jobs/types';

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

const historyPage = (results: OperationsQueueItem[]): OperationsQueuePage => ({
  count: results.length,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 20,
  results,
});

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
      { id: 'template-1', key: 'mtg-like-v1', label: 'Default card', definition_json: '{}' },
    ]);
    vi.mocked(fetchCurrentContentVersion).mockResolvedValue(currentVersion);
    vi.mocked(fetchImportJobs).mockResolvedValue([activeJob()]);
    vi.mocked(fetchOperationsQueuePage).mockResolvedValue(
      historyPage([
        historyItem('active-job', 'running'),
        historyItem('finished-job', 'completed'),
      ]),
    );
    vi.mocked(createImportJob).mockResolvedValue();
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
      expect(mounted.controller.activityLoaded.value).toBe(true);
    });

    expect(mounted.controller.activeJobs.value.map((job) => job.id)).toEqual(['active-job']);
    expect(mounted.controller.recentJobs.value.map((job) => job.id)).toEqual(['finished-job']);
    expect(fetchOperationsQueuePage).toHaveBeenCalledWith('imports', 1, 20);

    mounted.app.unmount();
  });

  test('keeps activity data when a manual refresh fails', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.activityLoaded.value).toBe(true));
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

  test('refreshes recent history when polling observes a finished active job', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.activityLoaded.value).toBe(true));
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

  test('submits the existing import payload and resets the native picker key', async () => {
    const mounted = mountController();
    await vi.waitFor(() => expect(mounted.controller.formLoaded.value).toBe(true));
    const file = new File(['image'], 'card.png', { type: 'image/png' });
    mounted.controller.pickedFiles.value = [file];
    const initialInputKey = mounted.controller.fileInputKey.value;

    await mounted.controller.createJobFromPicker();

    expect(createImportJob).toHaveBeenCalledWith({
      templateId: 'mtg-like-v1',
      contentVersionBase: '16.2',
      contentVersionDescription: 'Current release.',
      files: [file],
    });
    expect(mounted.controller.pickedFiles.value).toEqual([]);
    expect(mounted.controller.fileInputKey.value).toBe(initialInputKey + 1);
    expect(fetchOperationsQueuePage).toHaveBeenCalledTimes(2);

    mounted.app.unmount();
  });

  test('keeps activity usable when form options fail to load', async () => {
    vi.mocked(fetchTemplates).mockRejectedValueOnce(new Error('Templates unavailable'));
    const mounted = mountController();

    await vi.waitFor(() => {
      expect(mounted.controller.formLoaded.value).toBe(true);
      expect(mounted.controller.activityLoaded.value).toBe(true);
    });

    expect(mounted.controller.formErrorMessage.value).toBe('Import options could not be loaded.');
    expect(mounted.controller.activeJobs.value).toHaveLength(1);

    mounted.app.unmount();
  });
});

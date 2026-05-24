import { useDocumentVisibility, useIntervalFn } from '@vueuse/core';
import { computed, onMounted, ref, watch } from 'vue';
import { fetchTemplates } from '@/modules/admin/api/templates';
import type { TemplateRecord } from '@/modules/admin/types';
import { cancelImportJob, createImportJob, fetchImportJobs } from '@/modules/import-jobs/api';
import type { ImportJob } from '@/modules/import-jobs/types';
import {
  canCancelImportJob,
  extractImportJobErrorMessage,
  formatImportJobTimestamp,
  getImportJobProgressClass,
  getImportJobProgressPercent,
  getImportJobStatusClass,
  hasActiveImportJobs,
} from '@/modules/import-jobs/utils';

export const useImportJobsController = () => {
  const pickerTemplateId = ref('mtg-like-v1');
  const pickerMode = ref<'single' | 'directory'>('single');
  const pickedFiles = ref<File[]>([]);
  const errorMessage = ref('');
  const jobs = ref<ImportJob[]>([]);
  const isRefreshing = ref(false);
  const creatingJob = ref(false);
  const cancellingJobIds = ref<Set<string>>(new Set());
  const lastRefreshedAt = ref<string | null>(null);
  const templates = ref<TemplateRecord[]>([]);
  const documentVisibility = useDocumentVisibility();

  const queuedCount = computed(() => jobs.value.filter((job) => job.status === 'queued').length);
  const runningCount = computed(() => jobs.value.filter((job) => job.status === 'running').length);
  const cancelingCount = computed(() => jobs.value.filter((job) => job.status === 'canceling').length);
  const completedCount = computed(() => jobs.value.filter((job) => job.status === 'completed').length);
  const failedCount = computed(() => jobs.value.filter((job) => job.status === 'failed').length);
  const cancelledCount = computed(() => jobs.value.filter((job) => job.status === 'cancelled').length);
  const hasActiveJobs = computed(() => hasActiveImportJobs(jobs.value));

  const loadJobs = async (): Promise<void> => {
    isRefreshing.value = true;
    try {
      jobs.value = await fetchImportJobs();
      lastRefreshedAt.value = new Date().toLocaleTimeString();
    } finally {
      isRefreshing.value = false;
    }
  };

  const loadTemplates = async (): Promise<void> => {
    templates.value = await fetchTemplates();
    if (templates.value.length === 0) {
      pickerTemplateId.value = '';
      return;
    }
    const stillExists = templates.value.some((item) => item.key === pickerTemplateId.value);
    if (!stillExists) {
      pickerTemplateId.value = templates.value[0].key;
    }
  };

  const createJobFromPicker = async (): Promise<void> => {
    errorMessage.value = '';
    if (pickedFiles.value.length === 0) {
      errorMessage.value = 'Please select at least one file.';
      return;
    }

    creatingJob.value = true;
    try {
      await createImportJob(pickerTemplateId.value, pickedFiles.value);
      pickedFiles.value = [];
    } catch (error) {
      console.error('Create import from upload failed', error);
      errorMessage.value = extractImportJobErrorMessage(error);
      return;
    } finally {
      creatingJob.value = false;
    }

    try {
      await loadJobs();
    } catch (error) {
      console.error('Refresh imports after upload create failed', error);
      errorMessage.value = 'Import was created, but refreshing the jobs list failed.';
    }
  };

  const cancelJob = async (jobId: string): Promise<void> => {
    const next = new Set(cancellingJobIds.value);
    if (next.has(jobId)) return;
    next.add(jobId);
    cancellingJobIds.value = next;
    errorMessage.value = '';

    try {
      await cancelImportJob(jobId);
      await loadJobs();
    } catch (error) {
      console.error('Cancel import job failed', error);
      errorMessage.value = extractImportJobErrorMessage(error);
    } finally {
      const done = new Set(cancellingJobIds.value);
      done.delete(jobId);
      cancellingJobIds.value = done;
    }
  };

  const onSingleFileSelected = (event: Event): void => {
    const input = event.target as HTMLInputElement;
    pickedFiles.value = input.files ? Array.from(input.files).slice(0, 1) : [];
  };

  const onDirectorySelected = (event: Event): void => {
    const input = event.target as HTMLInputElement;
    pickedFiles.value = input.files ? Array.from(input.files) : [];
  };

  const pollJobs = async (): Promise<void> => {
    if (documentVisibility.value !== 'visible') return;
    if (!hasActiveJobs.value) return;
    try {
      await loadJobs();
    } catch (error) {
      console.error('Polling imports failed', error);
    }
  };

  const { pause: pausePolling, resume: resumePolling } = useIntervalFn(() => {
    void pollJobs();
  }, 2000, { immediate: false });

  watch(
    [documentVisibility, hasActiveJobs],
    ([visibility, hasActive]) => {
      if (visibility === 'visible' && hasActive) {
        resumePolling();
        void pollJobs();
        return;
      }

      pausePolling();
    },
    { immediate: true },
  );

  onMounted(async () => {
    await loadTemplates();
    await loadJobs();
  });

  return {
    pickerTemplateId,
    pickerMode,
    pickedFiles,
    errorMessage,
    jobs,
    isRefreshing,
    creatingJob,
    cancellingJobIds,
    lastRefreshedAt,
    templates,
    queuedCount,
    runningCount,
    cancelingCount,
    completedCount,
    failedCount,
    cancelledCount,
    loadJobs,
    createJobFromPicker,
    cancelJob,
    onSingleFileSelected,
    onDirectorySelected,
    canCancel: canCancelImportJob,
    progressPercent: getImportJobProgressPercent,
    statusClass: getImportJobStatusClass,
    progressClass: getImportJobProgressClass,
    formatTimestamp: formatImportJobTimestamp,
  };
};

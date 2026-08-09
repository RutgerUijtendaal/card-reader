import { useDocumentVisibility, useIntervalFn } from '@vueuse/core';
import { computed, onMounted, ref, watch } from 'vue';
import { fetchOperationsQueuePage } from '@/domain/operations/api';
import type { OperationsQueueItem } from '@/domain/operations/types';
import { fetchTemplates } from '@/domain/templates/api';
import type { TemplateRecord } from '@/domain/templates/types';
import {
  cancelImportJob,
  createImportJob,
  fetchCurrentContentVersion,
  fetchImportJobs,
} from '@/features/import-jobs/api';
import type { ContentVersion, ImportJob } from '@/features/import-jobs/types';
import {
  canCancelImportJob,
  extractImportJobErrorMessage,
  formatImportJobTimestamp,
  getContentVersionBaseError,
  getContentVersionBasePrefill,
  getContentVersionDescriptionPrefill,
  getImportJobProgressClass,
  getImportJobProgressPercent,
  getImportJobStatusClass,
  getImportSubmitLabel,
  getOperationsItemProgressPercent,
  getRecentImportJobs,
  hasActiveImportJobs,
  isTerminalImportStatus,
} from '@/features/import-jobs/utils/importJobUtils';

const IMPORT_HISTORY_PAGE_SIZE = 100;
const RECENT_IMPORT_JOB_LIMIT = 5;
const ACTIVITY_REFRESH_ERROR_MESSAGE = 'Import activity could not be refreshed.';

export const useImportJobsController = () => {
  const pickerTemplateId = ref('mtg-like-v1');
  const contentVersionBase = ref('');
  const contentVersionDescription = ref('');
  const currentContentVersion = ref<ContentVersion | null>(null);
  const pickedFiles = ref<File[]>([]);
  const fileInputKey = ref(0);
  const formErrorMessage = ref('');
  const activityActionErrorMessage = ref('');
  const activeJobsErrorMessage = ref('');
  const historyErrorMessage = ref('');
  const activeJobs = ref<ImportJob[]>([]);
  const historyItems = ref<OperationsQueueItem[]>([]);
  const formLoaded = ref(false);
  const activeJobsLoaded = ref(false);
  const historyLoaded = ref(false);
  const activeJobsRefreshing = ref(false);
  const historyRefreshing = ref(false);
  const creatingJob = ref(false);
  const cancellingJobIds = ref<Set<string>>(new Set());
  const lastRefreshedAt = ref<string | null>(null);
  const templates = ref<TemplateRecord[]>([]);
  const documentVisibility = useDocumentVisibility();
  let activeJobsRequestId = 0;
  let historyRequestId = 0;

  const queuedCount = computed(
    () => activeJobs.value.filter((job) => job.status === 'queued').length,
  );
  const runningCount = computed(
    () => activeJobs.value.filter((job) => job.status === 'running').length,
  );
  const cancelingCount = computed(
    () => activeJobs.value.filter((job) => job.status === 'canceling').length,
  );
  const hasActiveJobs = computed(() => hasActiveImportJobs(activeJobs.value));
  const activeJobIds = computed(() => new Set(activeJobs.value.map((job) => job.id)));
  const recentJobs = computed(() =>
    getRecentImportJobs(historyItems.value, activeJobIds.value),
  );
  const isRefreshing = computed(
    () => activeJobsRefreshing.value || historyRefreshing.value,
  );
  const activityErrorMessage = computed(
    () =>
      activityActionErrorMessage.value
      || activeJobsErrorMessage.value
      || historyErrorMessage.value,
  );
  const contentVersionBaseError = computed(() =>
    getContentVersionBaseError(contentVersionBase.value),
  );
  const hasValidVersionInput = computed(
    () =>
      contentVersionBaseError.value.length === 0 &&
      contentVersionDescription.value.trim().length > 0,
  );
  const submitButtonLabel = computed(() => {
    if (creatingJob.value) return 'Queueing Import...';
    return getImportSubmitLabel(contentVersionBase.value, currentContentVersion.value);
  });

  const loadActiveJobs = async (): Promise<boolean> => {
    const requestId = ++activeJobsRequestId;
    activeJobsRefreshing.value = true;
    const previousIds = new Set(activeJobs.value.map((job) => job.id));
    try {
      const nextJobs = await fetchImportJobs();
      if (requestId !== activeJobsRequestId) return false;
      activeJobs.value = nextJobs;
      activeJobsErrorMessage.value = '';
      lastRefreshedAt.value = new Date().toLocaleTimeString();
      return [...previousIds].some((jobId) => !nextJobs.some((job) => job.id === jobId));
    } catch (error) {
      if (requestId === activeJobsRequestId) {
        activeJobsErrorMessage.value = ACTIVITY_REFRESH_ERROR_MESSAGE;
      }
      throw error;
    } finally {
      if (requestId === activeJobsRequestId) {
        activeJobsLoaded.value = true;
        activeJobsRefreshing.value = false;
      }
    }
  };

  const loadRecentJobs = async (): Promise<void> => {
    const requestId = ++historyRequestId;
    historyRefreshing.value = true;
    try {
      const nextItems: OperationsQueueItem[] = [];
      let nextPage: number | null = 1;

      while (nextPage !== null) {
        const page = await fetchOperationsQueuePage(
          'imports',
          nextPage,
          IMPORT_HISTORY_PAGE_SIZE,
        );
        if (requestId !== historyRequestId) return;
        nextItems.push(...page.results);
        if (
          getRecentImportJobs(nextItems, activeJobIds.value, RECENT_IMPORT_JOB_LIMIT).length
          >= RECENT_IMPORT_JOB_LIMIT
        ) {
          break;
        }
        nextPage = page.next_page;
      }

      if (requestId === historyRequestId) {
        historyItems.value = nextItems;
        historyErrorMessage.value = '';
      }
    } catch (error) {
      if (requestId === historyRequestId) {
        historyErrorMessage.value = ACTIVITY_REFRESH_ERROR_MESSAGE;
      }
      throw error;
    } finally {
      if (requestId === historyRequestId) {
        historyLoaded.value = true;
        historyRefreshing.value = false;
      }
    }
  };

  const refreshActivity = async (): Promise<void> => {
    activityActionErrorMessage.value = '';
    const [activeResult, historyResult] = await Promise.allSettled([
      loadActiveJobs(),
      loadRecentJobs(),
    ]);
    if (activeResult.status !== 'fulfilled' || historyResult.status !== 'fulfilled') return;

    const historyHasMissingActiveWork = historyItems.value.some(
      (item) => !isTerminalImportStatus(item.status) && !activeJobIds.value.has(item.id),
    );
    if (activeResult.value || historyHasMissingActiveWork) {
      try {
        await loadRecentJobs();
      } catch (error) {
        console.error('Reconcile import history after activity refresh failed', error);
      }
    }
  };

  const loadTemplates = async (): Promise<void> => {
    templates.value = await fetchTemplates();
    if (templates.value.length === 0) {
      pickerTemplateId.value = '';
      return;
    }
    const stillExists = templates.value.some((item) => item.key === pickerTemplateId.value);
    if (!stillExists) pickerTemplateId.value = templates.value[0].key;
  };

  const loadCurrentContentVersion = async (): Promise<void> => {
    currentContentVersion.value = await fetchCurrentContentVersion();
    contentVersionBase.value = getContentVersionBasePrefill(currentContentVersion.value);
    contentVersionDescription.value = getContentVersionDescriptionPrefill(
      currentContentVersion.value,
    );
  };

  const loadFormOptions = async (): Promise<void> => {
    formErrorMessage.value = '';
    const results = await Promise.allSettled([loadTemplates(), loadCurrentContentVersion()]);
    formLoaded.value = true;
    if (results.some((result) => result.status === 'rejected')) {
      formErrorMessage.value = 'Import options could not be loaded.';
    }
  };

  const resetPickedFiles = (): void => {
    pickedFiles.value = [];
    fileInputKey.value += 1;
  };

  const setPickedFiles = (files: File[]): void => {
    pickedFiles.value = files;
  };

  const createJobFromPicker = async (): Promise<void> => {
    formErrorMessage.value = '';
    if (pickedFiles.value.length === 0) {
      formErrorMessage.value = 'Please select at least one file.';
      return;
    }
    if (contentVersionBaseError.value.length > 0) {
      formErrorMessage.value = contentVersionBaseError.value;
      return;
    }
    if (contentVersionDescription.value.trim().length === 0) {
      formErrorMessage.value = 'Please enter a version description.';
      return;
    }

    creatingJob.value = true;
    try {
      await createImportJob({
        templateId: pickerTemplateId.value,
        contentVersionBase: contentVersionBase.value.trim(),
        contentVersionDescription: contentVersionDescription.value.trim(),
        files: pickedFiles.value,
      });
      resetPickedFiles();
    } catch (error) {
      console.error('Create import from upload failed', error);
      formErrorMessage.value = extractImportJobErrorMessage(error);
      return;
    } finally {
      creatingJob.value = false;
    }

    const [versionResult] = await Promise.allSettled([
      loadCurrentContentVersion(),
      refreshActivity(),
    ]);
    if (versionResult.status === 'rejected') {
      console.error('Refresh content version after upload create failed', versionResult.reason);
      formErrorMessage.value = 'Import was created, but the content version could not be refreshed.';
    }
  };

  const cancelJob = async (jobId: string): Promise<void> => {
    const next = new Set(cancellingJobIds.value);
    if (next.has(jobId)) return;
    next.add(jobId);
    cancellingJobIds.value = next;
    activityActionErrorMessage.value = '';

    try {
      await cancelImportJob(jobId);
    } catch (error) {
      console.error('Cancel import job failed', error);
      activityActionErrorMessage.value = extractImportJobErrorMessage(error);
      return;
    } finally {
      const done = new Set(cancellingJobIds.value);
      done.delete(jobId);
      cancellingJobIds.value = done;
    }

    await refreshActivity();
  };

  const pollJobs = async (): Promise<void> => {
    if (
      documentVisibility.value !== 'visible'
      || !hasActiveJobs.value
      || activeJobsRefreshing.value
    ) return;
    try {
      const activeJobFinished = await loadActiveJobs();
      if (activeJobFinished) await loadRecentJobs();
    } catch (error) {
      console.error('Polling imports failed', error);
    }
  };

  const { pause: pausePolling, resume: resumePolling } = useIntervalFn(
    () => {
      void pollJobs();
    },
    2000,
    { immediate: false },
  );

  watch(
    [documentVisibility, hasActiveJobs],
    ([visibility, hasActive]) => {
      if (visibility === 'visible' && hasActive) {
        resumePolling();
        return;
      }
      pausePolling();
    },
    { immediate: true },
  );

  onMounted(() => {
    void loadFormOptions();
    void refreshActivity();
  });

  return {
    pickerTemplateId,
    contentVersionBase,
    contentVersionDescription,
    currentContentVersion,
    pickedFiles,
    fileInputKey,
    formErrorMessage,
    activityErrorMessage,
    activeJobs,
    recentJobs,
    formLoaded,
    activeJobsLoaded,
    historyLoaded,
    activeJobsRefreshing,
    historyRefreshing,
    isRefreshing,
    creatingJob,
    cancellingJobIds,
    lastRefreshedAt,
    templates,
    queuedCount,
    runningCount,
    cancelingCount,
    contentVersionBaseError,
    hasValidVersionInput,
    submitButtonLabel,
    refreshActivity,
    createJobFromPicker,
    cancelJob,
    setPickedFiles,
    clearPickedFiles: resetPickedFiles,
    pollJobs,
    canCancel: canCancelImportJob,
    progressPercent: getImportJobProgressPercent,
    recentProgressPercent: getOperationsItemProgressPercent,
    statusClass: getImportJobStatusClass,
    progressClass: getImportJobProgressClass,
    formatTimestamp: formatImportJobTimestamp,
  };
};

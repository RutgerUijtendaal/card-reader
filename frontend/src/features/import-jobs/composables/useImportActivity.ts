import { useDocumentVisibility, useIntervalFn } from '@vueuse/core';
import { computed, onMounted, ref, watch } from 'vue';
import { fetchOperationsQueuePage } from '@/domain/operations/api';
import type { OperationsQueueItem } from '@/domain/operations/types';
import {
  cancelImportJob,
  fetchImportJobDetail,
  fetchImportJobs,
} from '@/features/import-jobs/api';
import type { ImportJob, ImportJobDetail } from '@/features/import-jobs/types';
import {
  extractImportJobErrorMessage,
  getRecentImportJobs,
  hasActiveImportJobs,
  isTerminalImportStatus,
} from '@/features/import-jobs/utils/importJobUtils';

const IMPORT_HISTORY_PAGE_SIZE = 100;
const RECENT_IMPORT_JOB_LIMIT = 5;
const ACTIVITY_REFRESH_ERROR_MESSAGE = 'Import activity could not be refreshed.';
const DETAIL_REFRESH_ERROR_MESSAGE = 'Import details could not be refreshed.';

export const useImportActivity = () => {
  const activityActionErrorMessage = ref('');
  const activeJobsErrorMessage = ref('');
  const historyErrorMessage = ref('');
  const detailErrorMessage = ref('');
  const activeJobs = ref<ImportJob[]>([]);
  const historyItems = ref<OperationsQueueItem[]>([]);
  const activeJobsLoaded = ref(false);
  const historyLoaded = ref(false);
  const activeJobsRefreshing = ref(false);
  const historyRefreshing = ref(false);
  const cancellingJobIds = ref<Set<string>>(new Set());
  const lastRefreshedAt = ref<string | null>(null);
  const selectedJobId = ref<string | null>(null);
  const selectedJobDetail = ref<ImportJobDetail | null>(null);
  const detailLoading = ref(false);
  const documentVisibility = useDocumentVisibility();
  let activeJobsRequestId = 0;
  let historyRequestId = 0;
  let detailRequestId = 0;
  let detailSelectionRevision = 0;

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
    () => activeJobsRefreshing.value || historyRefreshing.value || detailLoading.value,
  );
  const activityErrorMessage = computed(
    () =>
      activityActionErrorMessage.value
      || activeJobsErrorMessage.value
      || historyErrorMessage.value
      || detailErrorMessage.value,
  );
  const hasRefreshableDetail = computed(
    () => selectedJobDetail.value !== null
      && !isTerminalImportStatus(selectedJobDetail.value.status),
  );
  const shouldPoll = computed(
    () => documentVisibility.value === 'visible'
      && (hasActiveJobs.value || hasRefreshableDetail.value),
  );

  const loadActiveJobs = async (): Promise<string[]> => {
    const requestId = ++activeJobsRequestId;
    activeJobsRefreshing.value = true;
    const previousIds = new Set(activeJobs.value.map((job) => job.id));
    try {
      const nextJobs = await fetchImportJobs();
      if (requestId !== activeJobsRequestId) return [];
      activeJobs.value = nextJobs;
      activeJobsErrorMessage.value = '';
      lastRefreshedAt.value = new Date().toLocaleTimeString();
      return [...previousIds].filter((jobId) => !nextJobs.some((job) => job.id === jobId));
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
        ) break;
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

  const historyHasActiveWorkMissingFromSnapshot = (): boolean =>
    historyItems.value.some(
      (item) => !isTerminalImportStatus(item.status) && !activeJobIds.value.has(item.id),
    );

  const reconcileMissingActiveWork = async (): Promise<void> => {
    if (!historyHasActiveWorkMissingFromSnapshot()) return;
    try {
      await loadActiveJobs();
      if (!historyHasActiveWorkMissingFromSnapshot()) return;
    } catch (error) {
      console.error('Reconcile active imports after activity refresh failed', error);
      return;
    }
    try {
      await loadRecentJobs();
    } catch (error) {
      console.error('Reconcile import history after active refresh failed', error);
    }
  };

  const refreshSelectedJobDetail = async (): Promise<void> => {
    const jobId = selectedJobId.value;
    const selectionRevision = detailSelectionRevision;
    const detail = selectedJobDetail.value;
    if (!jobId || detailLoading.value || (detail && isTerminalImportStatus(detail.status))) return;

    const requestId = ++detailRequestId;
    try {
      const nextDetail = await fetchImportJobDetail(jobId);
      if (
        requestId === detailRequestId
        && selectionRevision === detailSelectionRevision
        && selectedJobId.value === jobId
      ) {
        selectedJobDetail.value = nextDetail;
        detailErrorMessage.value = '';
      }
    } catch (error) {
      if (requestId === detailRequestId && selectionRevision === detailSelectionRevision) {
        detailErrorMessage.value = DETAIL_REFRESH_ERROR_MESSAGE;
      }
      throw error;
    }
  };

  const refreshActivity = async (): Promise<void> => {
    const [activeResult, historyResult] = await Promise.allSettled([
      loadActiveJobs(),
      loadRecentJobs(),
      refreshSelectedJobDetail(),
    ]);
    if (activeResult.status !== 'fulfilled' || historyResult.status !== 'fulfilled') return;
    const removedJobsMissingFromHistory = activeResult.value.some(
      (jobId) => !historyItems.value.some(
        (item) => item.id === jobId && isTerminalImportStatus(item.status),
      ),
    );
    if (removedJobsMissingFromHistory) {
      try {
        await loadRecentJobs();
      } catch (error) {
        console.error('Reconcile import history after activity refresh failed', error);
        return;
      }
    }
    await reconcileMissingActiveWork();
  };

  const viewJobDetail = async (jobId: string): Promise<void> => {
    detailSelectionRevision += 1;
    const selectionRevision = detailSelectionRevision;
    const requestId = ++detailRequestId;
    selectedJobId.value = jobId;
    selectedJobDetail.value = null;
    detailLoading.value = true;
    detailErrorMessage.value = '';
    activityActionErrorMessage.value = '';
    try {
      const detail = await fetchImportJobDetail(jobId);
      if (
        requestId === detailRequestId
        && selectionRevision === detailSelectionRevision
        && selectedJobId.value === jobId
      ) selectedJobDetail.value = detail;
    } catch (error) {
      if (requestId !== detailRequestId || selectionRevision !== detailSelectionRevision) return;
      console.error('Load import detail failed', error);
      detailErrorMessage.value = extractImportJobErrorMessage(error);
    } finally {
      if (requestId === detailRequestId && selectionRevision === detailSelectionRevision) {
        detailLoading.value = false;
      }
    }
  };

  const closeJobDetail = (): void => {
    detailSelectionRevision += 1;
    detailRequestId += 1;
    selectedJobId.value = null;
    selectedJobDetail.value = null;
    detailLoading.value = false;
    detailErrorMessage.value = '';
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

    activeJobs.value = activeJobs.value.map((job) =>
      job.id === jobId ? { ...job, status: 'canceling' } : job,
    );
    if (selectedJobDetail.value?.id === jobId) {
      detailRequestId += 1;
      selectedJobDetail.value = { ...selectedJobDetail.value, status: 'canceling' };
    }
    await refreshActivity();
  };

  const pollJobs = async (): Promise<void> => {
    if (!shouldPoll.value || activeJobsRefreshing.value) return;
    await refreshActivity();
  };

  const { pause: pausePolling, resume: resumePolling } = useIntervalFn(
    () => void pollJobs(),
    2000,
    { immediate: false },
  );

  watch(
    shouldPoll,
    (enabled) => {
      if (enabled) resumePolling();
      else pausePolling();
    },
    { immediate: true },
  );
  watch(documentVisibility, (visibility, previous) => {
    if (visibility === 'visible' && previous !== undefined && previous !== 'visible') {
      void refreshActivity();
    }
  });
  onMounted(() => void refreshActivity());

  return {
    activityActionErrorMessage,
    activityErrorMessage,
    activeJobs,
    recentJobs,
    activeJobsLoaded,
    historyLoaded,
    activeJobsRefreshing,
    historyRefreshing,
    isRefreshing,
    cancellingJobIds,
    lastRefreshedAt,
    selectedJobDetail,
    detailLoading,
    queuedCount,
    runningCount,
    cancelingCount,
    refreshActivity,
    cancelJob,
    viewJobDetail,
    closeJobDetail,
    pollJobs,
  };
};

import { useDocumentVisibility, useIntervalFn } from '@vueuse/core';
import { computed, onMounted, ref, shallowRef, watch } from 'vue';
import type { CardPool, CardRole } from '@/domain/cards/types/cardModels';
import { fetchOperationsQueuePage } from '@/domain/operations/api';
import type { OperationsQueueItem } from '@/domain/operations/types';
import { fetchTemplates } from '@/domain/templates/api';
import type { TemplateRecord } from '@/domain/templates/types';
import {
  cancelImportJob,
  createImportJob,
  fetchImportJobByCreationKey,
  fetchImportJobDetail,
  fetchCurrentContentVersion,
  fetchImportJobs,
} from '@/features/import-jobs/api';
import type { CreateImportJobInput } from '@/features/import-jobs/api';
import type { ContentVersion, ImportJob, ImportJobDetail } from '@/features/import-jobs/types';
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

type ImportCreateState =
  | { phase: 'idle' }
  | { phase: 'submitting' }
  | { phase: 'reconciling' }
  | { phase: 'uncertain' }
  | { phase: 'confirmed'; jobId: string };

const newCreationKey = (): string => globalThis.crypto.randomUUID();

const isAmbiguousCreateFailure = (error: unknown): boolean => {
  if (typeof error !== 'object' || error === null || !("response" in error)) return true;
  const status = (error as { response?: { status?: number } }).response?.status;
  return status === undefined || status >= 500;
};

export const useImportJobsController = () => {
  const pickerTemplateId = ref('mtg-like-v1');
  const cardPool = ref<CardPool>('player');
  const cardRoleMode = ref<'automatic' | 'override'>('automatic');
  const cardRoleOverride = ref<CardRole[]>([]);
  const creationKey = ref(newCreationKey());
  const createState = ref<ImportCreateState>({ phase: 'idle' });
  const pendingAttempt = shallowRef<CreateImportJobInput | null>(null);
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
  const currentContentVersionLoaded = ref(false);
  const activeJobsLoaded = ref(false);
  const historyLoaded = ref(false);
  const activeJobsRefreshing = ref(false);
  const historyRefreshing = ref(false);
  const creatingJob = ref(false);
  const cancellingJobIds = ref<Set<string>>(new Set());
  const lastRefreshedAt = ref<string | null>(null);
  const templates = ref<TemplateRecord[]>([]);
  const selectedJobDetail = ref<ImportJobDetail | null>(null);
  const detailLoading = ref(false);
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
    if (createState.value.phase === 'reconciling') return 'Checking Import...';
    if (createState.value.phase === 'uncertain') return 'Retry Locked Import';
    if (creatingJob.value) return 'Queueing Import...';
    return getImportSubmitLabel(contentVersionBase.value, currentContentVersion.value);
  });
  const formLocked = computed(() =>
    ['submitting', 'reconciling', 'uncertain'].includes(createState.value.phase),
  );

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

  const historyHasActiveWorkMissingFromSnapshot = (): boolean =>
    historyItems.value.some(
      (item) => !isTerminalImportStatus(item.status) && !activeJobIds.value.has(item.id),
    );

  const reconcileMissingActiveWork = async (): Promise<void> => {
    if (!historyHasActiveWorkMissingFromSnapshot()) return;

    try {
      const activeJobFinished = await loadActiveJobs();
      if (!activeJobFinished && !historyHasActiveWorkMissingFromSnapshot()) return;
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

  const refreshActivity = async (): Promise<void> => {
    activityActionErrorMessage.value = '';
    const [activeResult, historyResult] = await Promise.allSettled([
      loadActiveJobs(),
      loadRecentJobs(),
    ]);
    if (activeResult.status !== 'fulfilled' || historyResult.status !== 'fulfilled') return;

    if (activeResult.value) {
      try {
        await loadRecentJobs();
      } catch (error) {
        console.error('Reconcile import history after activity refresh failed', error);
        return;
      }
    }

    await reconcileMissingActiveWork();
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
    const initialBase = contentVersionBase.value;
    const initialDescription = contentVersionDescription.value;
    const nextVersion = await fetchCurrentContentVersion();
    currentContentVersion.value = nextVersion;
    if (contentVersionBase.value === initialBase) {
      contentVersionBase.value = getContentVersionBasePrefill(nextVersion);
    }
    if (contentVersionDescription.value === initialDescription) {
      contentVersionDescription.value = getContentVersionDescriptionPrefill(nextVersion);
    }
  };

  const loadFormOptions = async (): Promise<void> => {
    formErrorMessage.value = '';
    const currentVersionResult = loadCurrentContentVersion()
      .then(() => true)
      .catch(() => false)
      .finally(() => {
        currentContentVersionLoaded.value = true;
      });
    let templatesLoaded = true;
    try {
      await loadTemplates();
    } catch {
      templatesLoaded = false;
      formErrorMessage.value = 'Import options could not be loaded.';
    } finally {
      formLoaded.value = true;
    }

    if (!(await currentVersionResult) && templatesLoaded) {
      formErrorMessage.value =
        'Current content version could not be loaded. Enter the version details manually.';
    }
  };

  const resetPickedFiles = (): void => {
    pickedFiles.value = [];
    fileInputKey.value += 1;
  };

  const setPickedFiles = (files: File[]): void => {
    if (formLocked.value) return;
    pickedFiles.value = files;
  };

  const clearPickedFiles = (): void => {
    if (formLocked.value) return;
    resetPickedFiles();
  };

  const completeCreatedAttempt = (jobId: string): void => {
    createState.value = { phase: 'confirmed', jobId };
    pendingAttempt.value = null;
    resetPickedFiles();
    cardRoleMode.value = 'automatic';
    cardRoleOverride.value = [];
    creationKey.value = newCreationKey();
  };

  const abandonPendingAttempt = (): void => {
    if (!pendingAttempt.value) return;
    pendingAttempt.value = null;
    createState.value = { phase: 'idle' };
    creationKey.value = newCreationKey();
    formErrorMessage.value = '';
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

    const attempt = pendingAttempt.value ?? {
      creationKey: creationKey.value,
      templateId: pickerTemplateId.value,
      contentVersionBase: contentVersionBase.value.trim(),
      contentVersionDescription: contentVersionDescription.value.trim(),
      files: [...pickedFiles.value],
      cardPool: cardPool.value,
      cardRoleMode: cardRoleMode.value,
      cardRoleOverride: cardRoleMode.value === 'override' ? [...cardRoleOverride.value] : [],
    };
    pendingAttempt.value = attempt;
    creatingJob.value = true;
    createState.value = { phase: 'submitting' };
    let createdJobId: string | null = null;
    try {
      const result = await createImportJob(attempt);
      createdJobId = result.job_id;
    } catch (error) {
      console.error('Create import from upload failed', error);
      if (!isAmbiguousCreateFailure(error)) {
        pendingAttempt.value = null;
        createState.value = { phase: 'idle' };
        creationKey.value = newCreationKey();
        formErrorMessage.value = extractImportJobErrorMessage(error);
        return;
      }
      createState.value = { phase: 'reconciling' };
      try {
        const existing = await fetchImportJobByCreationKey(attempt.creationKey);
        if (existing) createdJobId = existing.job_id;
      } catch (lookupError) {
        console.error('Import creation-key reconciliation failed', lookupError);
      }
      if (!createdJobId) {
        createState.value = { phase: 'uncertain' };
        formErrorMessage.value =
          'The server outcome is uncertain. The exact files and settings are locked; retry this attempt or abandon it to edit.';
        return;
      }
    } finally {
      creatingJob.value = false;
    }

    if (!createdJobId) return;
    completeCreatedAttempt(createdJobId);

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

  const viewJobDetail = async (jobId: string): Promise<void> => {
    detailLoading.value = true;
    activityActionErrorMessage.value = '';
    try {
      selectedJobDetail.value = await fetchImportJobDetail(jobId);
    } catch (error) {
      console.error('Load import detail failed', error);
      activityActionErrorMessage.value = extractImportJobErrorMessage(error);
    } finally {
      detailLoading.value = false;
    }
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
      await reconcileMissingActiveWork();
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
    cardPool,
    cardRoleMode,
    cardRoleOverride,
    creationKey,
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
    currentContentVersionLoaded,
    activeJobsLoaded,
    historyLoaded,
    activeJobsRefreshing,
    historyRefreshing,
    isRefreshing,
    creatingJob,
    cancellingJobIds,
    lastRefreshedAt,
    templates,
    selectedJobDetail,
    detailLoading,
    queuedCount,
    runningCount,
    cancelingCount,
    contentVersionBaseError,
    hasValidVersionInput,
    submitButtonLabel,
    formLocked,
    createState,
    refreshActivity,
    createJobFromPicker,
    cancelJob,
    viewJobDetail,
    setPickedFiles,
    clearPickedFiles,
    abandonPendingAttempt,
    pollJobs,
    canCancel: canCancelImportJob,
    progressPercent: getImportJobProgressPercent,
    recentProgressPercent: getOperationsItemProgressPercent,
    statusClass: getImportJobStatusClass,
    progressClass: getImportJobProgressClass,
    formatTimestamp: formatImportJobTimestamp,
  };
};

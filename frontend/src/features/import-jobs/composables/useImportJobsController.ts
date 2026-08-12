import { useEventListener } from '@vueuse/core';
import { computed, onMounted, ref, shallowRef } from 'vue';
import type { CardRole } from '@/domain/cards/cardRoles';
import type { CardPool } from '@/domain/cards/cardPools';
import { fetchTemplates } from '@/domain/templates/api';
import type { TemplateRecord } from '@/domain/templates/types';
import {
  createImportJob,
  fetchImportJobByCreationKey,
  fetchCurrentContentVersion,
} from '@/features/import-jobs/api';
import type { CreateImportJobInput } from '@/features/import-jobs/api';
import type { ContentVersion } from '@/features/import-jobs/types';
import { useImportActivity } from '@/features/import-jobs/composables/useImportActivity';
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
} from '@/features/import-jobs/utils/importJobUtils';

export type ImportCreateState =
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
  const formLoaded = ref(false);
  const currentContentVersionLoaded = ref(false);
  const creatingJob = ref(false);
  const templates = ref<TemplateRecord[]>([]);
  const activity = useImportActivity();
  const {
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
  } = activity;
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
  const hasUnresolvedCreateAttempt = computed(() => pendingAttempt.value !== null);

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

  useEventListener(window, 'beforeunload', (event) => {
    if (!hasUnresolvedCreateAttempt.value) return;
    event.preventDefault();
    event.returnValue = '';
  });

  onMounted(() => {
    void loadFormOptions();
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
    hasUnresolvedCreateAttempt,
    createState,
    refreshActivity,
    createJobFromPicker,
    cancelJob,
    viewJobDetail,
    closeJobDetail,
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

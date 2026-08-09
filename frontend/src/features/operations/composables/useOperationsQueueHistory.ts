import { useDocumentVisibility, useIntervalFn } from '@vueuse/core';
import { computed, ref, watch } from 'vue';
import type { Ref } from 'vue';
import { fetchOperationsQueuePage } from '@/features/operations/api';
import type { OperationsQueuePage } from '@/features/operations/types';

const HISTORY_PAGE_SIZE = 20;

export const useOperationsQueueHistory = (
  queueKey: Ref<string | null>,
  pageNumber: Ref<number>,
) => {
  const page = ref<OperationsQueuePage | null>(null);
  const loading = ref(false);
  const refreshing = ref(false);
  const errorMessage = ref('');
  const documentVisibility = useDocumentVisibility();
  let latestRequestId = 0;
  let activeRequestCount = 0;

  const loadHistory = async (options: { preserve?: boolean } = {}): Promise<void> => {
    const requestedQueueKey = queueKey.value;
    const requestedPage = pageNumber.value;
    if (!requestedQueueKey) {
      page.value = null;
      errorMessage.value = '';
      return;
    }

    const requestId = ++latestRequestId;
    activeRequestCount += 1;
    const preserve = options.preserve === true && page.value !== null;
    loading.value = !preserve;
    refreshing.value = preserve;
    if (!preserve) page.value = null;
    errorMessage.value = '';
    try {
      const nextPage = await fetchOperationsQueuePage(
        requestedQueueKey,
        requestedPage,
        HISTORY_PAGE_SIZE,
      );
      if (
        requestId !== latestRequestId ||
        requestedQueueKey !== queueKey.value ||
        requestedPage !== pageNumber.value
      )
        return;
      page.value = nextPage;
    } catch (error) {
      if (requestId !== latestRequestId) return;
      console.error('Load operations queue history failed', error);
      errorMessage.value = 'Queue history could not be loaded.';
    } finally {
      activeRequestCount -= 1;
      if (requestId === latestRequestId) {
        loading.value = false;
        refreshing.value = false;
      }
    }
  };

  const pollHistory = (): void => {
    if (
      documentVisibility.value === 'visible' &&
      pageNumber.value === 1 &&
      activeRequestCount === 0
    ) {
      void loadHistory({ preserve: true });
    }
  };

  const { pause, resume } = useIntervalFn(pollHistory, 5000, { immediate: false });

  watch(
    [queueKey, pageNumber],
    () => {
      void loadHistory();
    },
    { immediate: true },
  );

  watch(
    documentVisibility,
    (visibility) => {
      if (visibility === 'visible') {
        resume();
      } else {
        pause();
      }
    },
    { immediate: true },
  );

  return {
    page,
    items: computed(() => page.value?.results ?? []),
    loading,
    refreshing,
    errorMessage,
    loadHistory,
  };
};

import { useDocumentVisibility, useIntervalFn } from '@vueuse/core';
import { onMounted, ref, watch } from 'vue';
import { fetchOperationsOverview } from '@/features/operations/api';
import type { OperationsOverview } from '@/features/operations/types';

export const useOperationsOverview = () => {
  const overview = ref<OperationsOverview | null>(null);
  const loading = ref(true);
  const refreshing = ref(false);
  const errorMessage = ref('');
  const documentVisibility = useDocumentVisibility();
  let latestRequestId = 0;
  let activeRequestCount = 0;

  const loadOverview = async (): Promise<void> => {
    const requestId = ++latestRequestId;
    activeRequestCount += 1;
    refreshing.value = true;
    try {
      const nextOverview = await fetchOperationsOverview();
      if (requestId !== latestRequestId) return;
      overview.value = nextOverview;
      errorMessage.value = '';
    } catch (error) {
      if (requestId !== latestRequestId) return;
      console.error('Load operations overview failed', error);
      errorMessage.value = 'Worker and queue status could not be loaded.';
    } finally {
      activeRequestCount -= 1;
      if (requestId === latestRequestId) {
        loading.value = false;
        refreshing.value = false;
      }
    }
  };

  const pollOverview = (): void => {
    if (activeRequestCount === 0) void loadOverview();
  };

  const { pause, resume } = useIntervalFn(
    pollOverview,
    5000,
    { immediate: false },
  );

  watch(
    documentVisibility,
    (visibility) => {
      if (visibility === 'visible') {
        resume();
        if (!loading.value) pollOverview();
      } else {
        pause();
      }
    },
    { immediate: true },
  );

  onMounted(() => void loadOverview());

  return { overview, loading, refreshing, errorMessage, loadOverview };
};

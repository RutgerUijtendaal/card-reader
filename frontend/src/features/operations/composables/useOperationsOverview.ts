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

  const loadOverview = async (): Promise<void> => {
    refreshing.value = true;
    try {
      overview.value = await fetchOperationsOverview();
      errorMessage.value = '';
    } catch (error) {
      console.error('Load operations overview failed', error);
      errorMessage.value = 'Worker and queue status could not be loaded.';
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  };

  const { pause, resume } = useIntervalFn(
    () => void loadOverview(),
    5000,
    { immediate: false },
  );

  watch(
    documentVisibility,
    (visibility) => {
      if (visibility === 'visible') {
        resume();
        if (!loading.value) void loadOverview();
      } else {
        pause();
      }
    },
    { immediate: true },
  );

  onMounted(() => void loadOverview());

  return { overview, loading, refreshing, errorMessage, loadOverview };
};

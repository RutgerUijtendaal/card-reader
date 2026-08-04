import { ref } from 'vue';
import { fetchAccessRequestSummary } from '@/domain/access-requests/api';
import { usePollingSummary } from '@/shared/composables/usePollingSummary';
import { useAuthStore } from '@/domain/session/store';

const pendingAccessRequestCount = ref(0);

export function useAccessRequestSummary() {
  const auth = useAuthStore();
  const summary = usePollingSummary('access-requests', {
    canLoad: () => auth.canManageUsers,
    reset: () => {
      pendingAccessRequestCount.value = 0;
    },
    load: async () => {
      const response = await fetchAccessRequestSummary();
      pendingAccessRequestCount.value = response.pending_access_request_count;
    },
  });

  const setPendingAccessRequestCount = (count: number): void => {
    pendingAccessRequestCount.value = Math.max(0, count);
  };

  const decrementPendingAccessRequestCount = (amount = 1): void => {
    setPendingAccessRequestCount(pendingAccessRequestCount.value - amount);
  };

  return {
    pendingAccessRequestCount,
    loadingAccessRequestSummary: summary.loading,
    loadAccessRequestSummary: summary.load,
    setPendingAccessRequestCount,
    decrementPendingAccessRequestCount,
  };
}

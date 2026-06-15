import { ref } from 'vue';
import { api } from '@/api/client';
import { usePollingSummary } from '@/composables/usePollingSummary';
import { useAuthStore } from '@/modules/auth/authStore';

type AccessRequestSummaryResponse = {
  pending_access_request_count: number;
};

const pendingAccessRequestCount = ref(0);

export function useAccessRequestSummary() {
  const auth = useAuthStore();
  const summary = usePollingSummary('access-requests', {
    canLoad: () => auth.canManageUsers,
    reset: () => {
      pendingAccessRequestCount.value = 0;
    },
    load: async () => {
      const response = await api.get<AccessRequestSummaryResponse>('/admin/access-requests/summary');
      pendingAccessRequestCount.value = response.data.pending_access_request_count;
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

import { ref } from 'vue';
import { api } from '@/api/client';
import { useAuthStore } from '@/modules/auth/authStore';
import { usePollingSummary } from '@/composables/usePollingSummary';

type ReviewSummaryResponse = {
  open_parse_flag_item_count: number;
};

const openParseFlagItemCount = ref(0);

export function useReviewSummary() {
  const auth = useAuthStore();
  const summary = usePollingSummary('review', {
    canLoad: () => auth.canAccessStaffRoutes,
    reset: () => {
      openParseFlagItemCount.value = 0;
    },
    load: async () => {
      const response = await api.get<ReviewSummaryResponse>('/review/summary');
      openParseFlagItemCount.value = response.data.open_parse_flag_item_count;
    },
  });

  const decrementOpenParseFlagItemCount = (amount = 1): void => {
    openParseFlagItemCount.value = Math.max(0, openParseFlagItemCount.value - amount);
  };

  const incrementOpenParseFlagItemCount = (amount = 1): void => {
    openParseFlagItemCount.value += amount;
  };

  return {
    openParseFlagItemCount,
    loadingReviewSummary: summary.loading,
    loadReviewSummary: summary.load,
    decrementOpenParseFlagItemCount,
    incrementOpenParseFlagItemCount,
  };
}

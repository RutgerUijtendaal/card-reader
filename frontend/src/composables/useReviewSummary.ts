import { ref } from 'vue';
import { api } from '@/api/client';
import { useAuthStore } from '@/modules/auth/authStore';

type ReviewSummaryResponse = {
  open_parse_flag_item_count: number;
};

const openParseFlagItemCount = ref(0);
const loadingReviewSummary = ref(false);

export function useReviewSummary() {
  const auth = useAuthStore();

  const loadReviewSummary = async (): Promise<void> => {
    if (!auth.canAccessStaffRoutes) {
      openParseFlagItemCount.value = 0;
      return;
    }
    loadingReviewSummary.value = true;
    try {
      const response = await api.get<ReviewSummaryResponse>('/review/summary');
      openParseFlagItemCount.value = response.data.open_parse_flag_item_count;
    } catch {
      openParseFlagItemCount.value = 0;
    } finally {
      loadingReviewSummary.value = false;
    }
  };

  const decrementOpenParseFlagItemCount = (amount = 1): void => {
    openParseFlagItemCount.value = Math.max(0, openParseFlagItemCount.value - amount);
  };

  const incrementOpenParseFlagItemCount = (amount = 1): void => {
    openParseFlagItemCount.value += amount;
  };

  return {
    openParseFlagItemCount,
    loadingReviewSummary,
    loadReviewSummary,
    decrementOpenParseFlagItemCount,
    incrementOpenParseFlagItemCount,
  };
}

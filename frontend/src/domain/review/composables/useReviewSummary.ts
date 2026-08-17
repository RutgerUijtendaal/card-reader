import { ref } from 'vue';
import { fetchReviewSummary } from '@/domain/review/api';
import { useAuthStore } from '@/domain/session/store';
import { usePollingSummary } from '@/shared/composables/usePollingSummary';

const openParseFlagItemCount = ref(0);
const openClassificationReviewCount = ref(0);
const openReviewCount = ref(0);

export function useReviewSummary() {
  const auth = useAuthStore();
  const summary = usePollingSummary('review', {
    canLoad: () => auth.canAccessStaffRoutes,
    reset: () => {
      openParseFlagItemCount.value = 0;
      openClassificationReviewCount.value = 0;
      openReviewCount.value = 0;
    },
    load: async () => {
      const response = await fetchReviewSummary();
      openParseFlagItemCount.value = response.open_parse_flag_item_count;
      openClassificationReviewCount.value = response.open_classification_review_count;
      openReviewCount.value = response.open_review_count;
    },
  });

  const decrementOpenParseFlagItemCount = (amount = 1): void => {
    openParseFlagItemCount.value = Math.max(0, openParseFlagItemCount.value - amount);
    openReviewCount.value = Math.max(0, openReviewCount.value - amount);
  };

  const incrementOpenParseFlagItemCount = (amount = 1): void => {
    openParseFlagItemCount.value += amount;
    openReviewCount.value += amount;
  };

  const decrementOpenClassificationReviewCount = (amount = 1): void => {
    openClassificationReviewCount.value = Math.max(0, openClassificationReviewCount.value - amount);
    openReviewCount.value = Math.max(0, openReviewCount.value - amount);
  };

  return {
    openParseFlagItemCount,
    openClassificationReviewCount,
    openReviewCount,
    loadingReviewSummary: summary.loading,
    loadReviewSummary: summary.load,
    decrementOpenParseFlagItemCount,
    incrementOpenParseFlagItemCount,
    decrementOpenClassificationReviewCount,
  };
}

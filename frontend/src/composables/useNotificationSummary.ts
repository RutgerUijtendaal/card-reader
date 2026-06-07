import { ref } from 'vue';
import { fetchNotificationSummary } from '@/modules/notifications/api';
import { useAuthStore } from '@/modules/auth/authStore';
import { usePollingSummary } from '@/composables/usePollingSummary';

const unreadNotificationCount = ref(0);

export function useNotificationSummary() {
  const auth = useAuthStore();
  const summary = usePollingSummary('notifications', {
    canLoad: () => auth.authEnabled && auth.authenticated,
    reset: () => {
      unreadNotificationCount.value = 0;
    },
    load: async () => {
      const response = await fetchNotificationSummary();
      unreadNotificationCount.value = response.unread_count;
    },
  });

  const setUnreadNotificationCount = (count: number): void => {
    unreadNotificationCount.value = Math.max(0, count);
  };

  const decrementUnreadNotificationCount = (amount = 1): void => {
    unreadNotificationCount.value = Math.max(0, unreadNotificationCount.value - amount);
  };

  const incrementUnreadNotificationCount = (amount = 1): void => {
    unreadNotificationCount.value += amount;
  };

  return {
    unreadNotificationCount,
    loadingNotificationSummary: summary.loading,
    loadNotificationSummary: summary.load,
    setUnreadNotificationCount,
    decrementUnreadNotificationCount,
    incrementUnreadNotificationCount,
  };
}

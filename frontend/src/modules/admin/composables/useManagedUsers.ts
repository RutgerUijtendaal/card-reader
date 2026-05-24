import { ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  createManagedUser,
  deactivateManagedUser,
  fetchManagedUsers,
  resetManagedUserPassword,
  restoreManagedUser,
} from '@/modules/admin/api/users';
import type { ManagedUserRecord, PasswordSetupResponse } from '@/modules/admin/types';

export const useManagedUsers = () => {
  const users = ref<ManagedUserRecord[]>([]);
  const unmanagedUsers = ref<ManagedUserRecord[]>([]);
  const includeInactive = ref(false);
  const loading = ref(false);
  const setupResponse = ref<PasswordSetupResponse | null>(null);

  const loadUsers = async (): Promise<void> => {
    loading.value = true;
    try {
      const response = await fetchManagedUsers(includeInactive.value);
      users.value = response.managed_results;
      unmanagedUsers.value = response.unmanaged_results;
    } catch (error) {
      toast.error(extractErrorMessage(error, 'Failed to load users.'));
    } finally {
      loading.value = false;
    }
  };

  const createUser = async (username: string): Promise<void> => {
    setupResponse.value = await createManagedUser({ username });
    await loadUsers();
  };

  const deactivateUser = async (userId: string): Promise<void> => {
    await deactivateManagedUser(userId);
    await loadUsers();
  };

  const restoreUser = async (userId: string): Promise<void> => {
    await restoreManagedUser(userId);
    await loadUsers();
  };

  const resetPassword = async (userId: string): Promise<void> => {
    setupResponse.value = await resetManagedUserPassword(userId);
  };

  watch(includeInactive, () => {
    void loadUsers();
  });

  return {
    users,
    unmanagedUsers,
    includeInactive,
    loading,
    setupResponse,
    loadUsers,
    createUser,
    deactivateUser,
    restoreUser,
    resetPassword,
  };
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }
  }
  return fallback;
};

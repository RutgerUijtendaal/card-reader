import { ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { useAccessRequestSummary } from '@/domain/access-requests/composables/useAccessRequestSummary';
import { getApiErrorMessage as extractErrorMessage } from '@/shared/api/errors';
import {
  approveAccessRequest,
  createManagedUser,
  deactivateManagedUser,
  declineAccessRequest,
  fetchAccessRequests,
  fetchManagedUsers,
  resetManagedUserPassword,
  restoreManagedUser,
  updateManagedUser,
} from '@/features/admin/api/users';
import type { AccessRequestRecord, ManagedUserRecord, PasswordSetupResponse } from '@/features/admin/types';

export const useManagedUsers = () => {
  const { setPendingAccessRequestCount } = useAccessRequestSummary();
  const users = ref<ManagedUserRecord[]>([]);
  const unmanagedUsers = ref<ManagedUserRecord[]>([]);
  const accessRequests = ref<AccessRequestRecord[]>([]);
  const includeInactive = ref(false);
  const includeResolvedAccessRequests = ref(false);
  const loading = ref(false);
  const loadingAccessRequests = ref(false);
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

  const loadAccessRequests = async (): Promise<void> => {
    loadingAccessRequests.value = true;
    try {
      accessRequests.value = await fetchAccessRequests(
        includeResolvedAccessRequests.value ? 'all' : 'pending',
      );
      setPendingAccessRequestCount(
        accessRequests.value.filter((request) => request.status === 'pending').length,
      );
    } catch (error) {
      toast.error(extractErrorMessage(error, 'Failed to load access requests.'));
    } finally {
      loadingAccessRequests.value = false;
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

  const setDeveloperAccess = async (userId: string, enabled: boolean): Promise<void> => {
    const updated = await updateManagedUser(userId, { is_developer: enabled });
    const index = users.value.findIndex((user) => user.id === userId);
    if (index >= 0) {
      users.value[index] = updated;
    }
  };

  const approveRequest = async (accessRequestId: string, username: string): Promise<void> => {
    const response = await approveAccessRequest(accessRequestId, username);
    setupResponse.value = response.password_setup;
    await Promise.all([loadAccessRequests(), loadUsers()]);
  };

  const declineRequest = async (accessRequestId: string): Promise<void> => {
    await declineAccessRequest(accessRequestId);
    await loadAccessRequests();
  };

  watch(includeInactive, () => {
    void loadUsers();
  });

  watch(includeResolvedAccessRequests, () => {
    void loadAccessRequests();
  });

  return {
    users,
    unmanagedUsers,
    accessRequests,
    includeInactive,
    includeResolvedAccessRequests,
    loading,
    loadingAccessRequests,
    setupResponse,
    loadUsers,
    loadAccessRequests,
    createUser,
    deactivateUser,
    restoreUser,
    resetPassword,
    setDeveloperAccess,
    approveRequest,
    declineRequest,
  };
};

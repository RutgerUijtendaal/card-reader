import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import {
  applySessionCsrfToken,
  fetchCurrentUser as fetchCurrentUserRequest,
  loginUser,
  logoutUser,
} from '@/domain/session/api';
import type { CurrentUser, LoginCredentials } from './types';
import type { CardPool } from '@/domain/cards/cardPools';

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null);
  const initialized = ref(false);
  const loading = ref(false);

  const authenticated = computed(() => user.value?.authenticated ?? false);
  const canAccessStaffRoutes = computed(() => user.value?.can_access_admin === true);
  const accessibleCardPools = computed<readonly CardPool[]>(
    () => user.value?.accessible_card_pools ?? ['player'],
  );
  const canManageUsers = computed(() => user.value?.can_manage_users === true);
  const canAccessMaintenance = computed(() => user.value?.can_access_maintenance === true);
  const canDownloadDeveloperData = computed(() => user.value?.can_download_developer_data === true);
  const canManageDeveloperData = computed(() => user.value?.can_manage_developer_data === true);

  const fetchCurrentUser = async (): Promise<CurrentUser> => {
    loading.value = true;
    try {
      const currentUser = await fetchCurrentUserRequest();
      user.value = currentUser;
      applySessionCsrfToken(currentUser);
      return currentUser;
    } catch {
      const fallback = { authenticated: false };
      user.value = fallback;
      return fallback;
    } finally {
      initialized.value = true;
      loading.value = false;
    }
  };

  const login = async (credentials: LoginCredentials): Promise<CurrentUser> => {
    loading.value = true;
    try {
      const currentUser = await loginUser(credentials);
      user.value = currentUser;
      applySessionCsrfToken(currentUser);
      initialized.value = true;
      return currentUser;
    } finally {
      loading.value = false;
    }
  };

  const logout = async (): Promise<void> => {
    await logoutUser();
    user.value = { authenticated: false };
    initialized.value = true;
  };

  return {
    user,
    initialized,
    loading,
    authenticated,
    canAccessStaffRoutes,
    accessibleCardPools,
    canManageUsers,
    canAccessMaintenance,
    canDownloadDeveloperData,
    canManageDeveloperData,
    fetchCurrentUser,
    login,
    logout,
  };
});

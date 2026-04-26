import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { api } from '@/api/client';
import type { CurrentUser, LoginCredentials } from './types';

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null);
  const initialized = ref(false);
  const loading = ref(false);

  const authEnabled = computed(() => user.value?.auth_enabled ?? true);
  const authenticated = computed(() => user.value?.authenticated ?? false);
  const canAccessStaffRoutes = computed(
    () => !authEnabled.value || (authenticated.value && user.value?.is_staff === true),
  );
  const canAccessMaintenance = computed(
    () => !authEnabled.value || (authenticated.value && user.value?.is_superuser === true),
  );

  const applyCsrfToken = (currentUser: CurrentUser): void => {
    const token = currentUser.csrf_token;
    if (token) {
      api.defaults.headers.common['X-CSRFToken'] = token;
    }
  };

  const fetchCurrentUser = async (): Promise<CurrentUser> => {
    loading.value = true;
    try {
      const response = await api.get<CurrentUser>('/auth/me');
      user.value = response.data;
      applyCsrfToken(response.data);
      return response.data;
    } catch {
      const fallback = { auth_enabled: true, authenticated: false };
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
      const response = await api.post<CurrentUser>('/auth/login', credentials);
      user.value = response.data;
      applyCsrfToken(response.data);
      initialized.value = true;
      return response.data;
    } finally {
      loading.value = false;
    }
  };

  const logout = async (): Promise<void> => {
    await api.post('/auth/logout');
    user.value = { auth_enabled: authEnabled.value, authenticated: false };
    initialized.value = true;
  };

  return {
    user,
    initialized,
    loading,
    authEnabled,
    authenticated,
    canAccessStaffRoutes,
    canAccessMaintenance,
    fetchCurrentUser,
    login,
    logout,
  };
});

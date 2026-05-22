import { api } from '@/api/client';
import type {
  CreateManagedUserRequest,
  ManagedUserListResponse,
  ManagedUserRecord,
  PasswordSetupResponse,
} from '@/modules/settings/types';

export const fetchManagedUsers = async (
  includeInactive: boolean,
): Promise<ManagedUserListResponse> => {
  const response = await api.get<ManagedUserListResponse>('/settings/users', {
    params: { include_inactive: includeInactive },
  });
  return response.data;
};

export const createManagedUser = async (
  payload: CreateManagedUserRequest,
): Promise<PasswordSetupResponse> => {
  const response = await api.post<PasswordSetupResponse>('/settings/users', payload);
  return response.data;
};

export const deactivateManagedUser = async (userId: string): Promise<void> => {
  await api.delete(`/settings/users/${userId}`);
};

export const restoreManagedUser = async (userId: string): Promise<ManagedUserRecord> => {
  const response = await api.post<ManagedUserRecord>(`/settings/users/${userId}/restore`);
  return response.data;
};

export const resetManagedUserPassword = async (userId: string): Promise<PasswordSetupResponse> => {
  const response = await api.post<PasswordSetupResponse>(`/settings/users/${userId}/reset-password`);
  return response.data;
};

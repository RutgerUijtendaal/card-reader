import { api } from '@/api/client';
import type {
  CreateManagedUserRequest,
  ManagedUserListResponse,
  ManagedUserRecord,
  PasswordSetupResponse,
} from '@/modules/admin/types';

export const fetchManagedUsers = async (
  includeInactive: boolean,
): Promise<ManagedUserListResponse> => {
  const response = await api.get<ManagedUserListResponse>('/admin/users', {
    params: { include_inactive: includeInactive },
  });
  return response.data;
};

export const createManagedUser = async (
  payload: CreateManagedUserRequest,
): Promise<PasswordSetupResponse> => {
  const response = await api.post<PasswordSetupResponse>('/admin/users', payload);
  return response.data;
};

export const deactivateManagedUser = async (userId: string): Promise<void> => {
  await api.delete(`/admin/users/${userId}`);
};

export const restoreManagedUser = async (userId: string): Promise<ManagedUserRecord> => {
  const response = await api.post<ManagedUserRecord>(`/admin/users/${userId}/restore`);
  return response.data;
};

export const resetManagedUserPassword = async (userId: string): Promise<PasswordSetupResponse> => {
  const response = await api.post<PasswordSetupResponse>(`/admin/users/${userId}/reset-password`);
  return response.data;
};

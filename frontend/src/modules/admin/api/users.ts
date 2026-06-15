import { api } from '@/api/client';
import type {
  AccessRequestApprovalResponse,
  AccessRequestRecord,
  AccessRequestStatusFilter,
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

export const fetchAccessRequests = async (
  status: AccessRequestStatusFilter,
): Promise<AccessRequestRecord[]> => {
  const response = await api.get<AccessRequestRecord[]>('/admin/access-requests', {
    params: { status },
  });
  return response.data;
};

export const approveAccessRequest = async (
  accessRequestId: string,
  username: string,
): Promise<AccessRequestApprovalResponse> => {
  const response = await api.post<AccessRequestApprovalResponse>(
    `/admin/access-requests/${accessRequestId}/approve`,
    { username },
  );
  return response.data;
};

export const declineAccessRequest = async (
  accessRequestId: string,
): Promise<AccessRequestRecord> => {
  const response = await api.post<AccessRequestRecord>(
    `/admin/access-requests/${accessRequestId}/decline`,
  );
  return response.data;
};

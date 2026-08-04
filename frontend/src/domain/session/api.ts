import { api } from '@/shared/api/client';
import type {
  AccessRequestSubmission,
  CurrentUser,
  LoginCredentials,
  PasswordSetupRequest,
  PasswordSetupValidationResponse,
} from './types';

export const applySessionCsrfToken = (currentUser: CurrentUser): void => {
  if (currentUser.csrf_token) {
    api.defaults.headers.common['X-CSRFToken'] = currentUser.csrf_token;
  }
};

export const fetchCurrentUser = async (): Promise<CurrentUser> => {
  const response = await api.get<CurrentUser>('/auth/me');
  return response.data;
};

export const loginUser = async (credentials: LoginCredentials): Promise<CurrentUser> => {
  const response = await api.post<CurrentUser>('/auth/login', credentials);
  return response.data;
};

export const logoutUser = async (): Promise<void> => {
  await api.post('/auth/logout');
};

export const validatePasswordSetupLink = async (
  uid: string,
  token: string,
): Promise<PasswordSetupValidationResponse> => {
  const response = await api.get<PasswordSetupValidationResponse>('/auth/password/setup', {
    params: { uid, token },
  });
  return response.data;
};

export const submitPasswordSetup = async (
  payload: PasswordSetupRequest,
): Promise<{ message: string; username: string }> => {
  const response = await api.post<{ message: string; username: string }>(
    '/auth/password/setup',
    payload,
  );
  return response.data;
};

export const submitAccessRequest = async (payload: {
  contact_handle: string;
  message: string;
}): Promise<AccessRequestSubmission> => {
  const response = await api.post<AccessRequestSubmission>('/auth/access-requests', payload);
  return response.data;
};

import { api } from '@/api/client';
import type { PasswordSetupRequest, PasswordSetupValidationResponse } from './types';

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

import { api } from '@/shared/api/client';
import type { CardVersionDetail } from '@/domain/cards/types';
import type { ParseFlagCreatePayload } from '@/domain/review/types';

export const patchLatestCardVersion = async (
  cardId: string,
  payload: Record<string, unknown>,
): Promise<CardVersionDetail> => {
  const response = await api.patch<CardVersionDetail>(`/cards/${cardId}/latest-version`, payload);
  return response.data;
};

export const queueCardReparse = async (cardId: string, templateId: string): Promise<string> => {
  const response = await api.post<{ message: string }>(`/cards/${cardId}/reparse`, {
    template_id: templateId,
  });
  return response.data.message;
};

export const promoteCardVersion = async (
  cardId: string,
  versionId: string,
): Promise<CardVersionDetail> => {
  const response = await api.post<CardVersionDetail>(`/cards/${cardId}/versions/${versionId}/promote`);
  return response.data;
};

export const submitCardParseFlag = async (
  cardId: string,
  versionId: string,
  payload: ParseFlagCreatePayload,
): Promise<void> => {
  await api.post(`/cards/${cardId}/versions/${versionId}/flags`, payload);
};

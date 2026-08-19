import { api } from '@/shared/api/client';
import type { CardVersionDetail } from '@/domain/cards/types';
import type { ParseFlagCreatePayload } from '@/domain/review/types';

export const patchLatestCardVersion = async <TCardVersion = CardVersionDetail>(
  cardId: string,
  payload: Record<string, unknown>,
): Promise<TCardVersion> => {
  const response = await api.patch<TCardVersion>(`/cards/${cardId}/latest-version`, payload);
  return response.data;
};

export const queueCardReparse = async (cardId: string, templateId: string): Promise<string> => {
  const response = await api.post<{ message: string }>(`/cards/${cardId}/reparse`, {
    template_id: templateId,
  });
  return response.data.message;
};

export const promoteCardVersion = async <TCardVersion = CardVersionDetail>(
  cardId: string,
  versionId: string,
): Promise<TCardVersion> => {
  const response = await api.post<TCardVersion>(`/cards/${cardId}/versions/${versionId}/promote`);
  return response.data;
};

export const submitCardParseFlag = async (
  cardId: string,
  versionId: string,
  payload: ParseFlagCreatePayload,
): Promise<void> => {
  await api.post(`/cards/${cardId}/versions/${versionId}/flags`, payload);
};

import { api } from '@/shared/api/client';
import type { ContentVersionRecord } from '@/features/admin/types';
import type { CardListItem } from '@/domain/cards/types';

export const fetchContentVersions = async (): Promise<ContentVersionRecord[]> => {
  const response = await api.get<ContentVersionRecord[]>('/admin/content-versions');
  return response.data;
};

export const fetchContentVersionCards = async (versionId: string): Promise<CardListItem[]> => {
  const response = await api.get<CardListItem[]>(`/admin/content-versions/${versionId}/cards`);
  return response.data;
};

export const updateContentVersion = async (
  versionId: string,
  payload: { version_number: string; description: string },
): Promise<ContentVersionRecord> => {
  const response = await api.patch<ContentVersionRecord>(`/admin/content-versions/${versionId}`, payload);
  return response.data;
};

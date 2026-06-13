import { api } from '@/api/client';
import type { CardBackCurrentResponse, CardBackRecord } from '@/modules/admin/types';

export const fetchCurrentCardBack = async (): Promise<CardBackCurrentResponse> => {
  const response = await api.get<CardBackCurrentResponse>('/card-backs/current');
  return response.data;
};

export const fetchCardBacks = async (): Promise<CardBackRecord[]> => {
  const response = await api.get<CardBackRecord[]>('/admin/card-backs');
  return response.data;
};

export const uploadCardBack = async (file: File, label: string): Promise<CardBackRecord> => {
  const formData = new FormData();
  formData.append('file', file);
  const normalizedLabel = label.trim();
  if (normalizedLabel.length > 0) {
    formData.append('label', normalizedLabel);
  }
  const response = await api.post<CardBackRecord>('/admin/card-backs/upload', formData);
  return response.data;
};

export const activateCardBack = async (cardBackId: string): Promise<CardBackRecord> => {
  const response = await api.post<CardBackRecord>(`/admin/card-backs/${cardBackId}/activate`);
  return response.data;
};

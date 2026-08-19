import { api } from '@/shared/api/client';
import type { CardPool } from '@/domain/cards/cardPools';
import type {
  CardBackCurrentResponse,
  CardBackDefaults,
  CardBackRecord,
  PublicCardBackRecord,
} from '@/domain/card-backs/types';

export const fetchCurrentCardBack = async (): Promise<CardBackCurrentResponse> => {
  const response = await api.get<CardBackCurrentResponse>('/card-backs/current');
  return response.data;
};

export const fetchCardBacks = async (): Promise<CardBackRecord[]> => {
  const response = await api.get<CardBackRecord[]>('/admin/card-backs');
  return response.data;
};

export const fetchCardBackDefaults = async (): Promise<CardBackDefaults> => {
  const response = await api.get<CardBackDefaults>('/card-backs/defaults');
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

export const setPoolCardBackDefault = async (
  cardPool: CardPool,
  cardBackId: string | null,
): Promise<PublicCardBackRecord | null> => {
  const response = await api.put<PublicCardBackRecord | null>(`/admin/card-backs/defaults/${cardPool}`, {
    card_back_id: cardBackId,
  });
  return response.data;
};

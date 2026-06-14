import { api } from '@/api/client';
import type { CardBackCurrentResponse } from '@/modules/playtester/types';

export const fetchCurrentCardBack = async (): Promise<CardBackCurrentResponse> => {
  const response = await api.get<CardBackCurrentResponse>('/card-backs/current');
  return response.data;
};

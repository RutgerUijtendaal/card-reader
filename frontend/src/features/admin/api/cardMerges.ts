import { api } from '@/shared/api/client';
import type { CardMergeApplyResponse, CardMergePreview } from '@/features/admin/types';

type CardMergeRequest = {
  target_card_id: string;
  source_card_ids: string[];
};

export const previewCardMerge = async (payload: CardMergeRequest): Promise<CardMergePreview> => {
  const response = await api.post<CardMergePreview>('/admin/card-merges/preview', payload);
  return response.data;
};

export const applyCardMerge = async (payload: CardMergeRequest): Promise<CardMergeApplyResponse> => {
  const response = await api.post<CardMergeApplyResponse>('/admin/card-merges/apply', payload);
  return response.data;
};

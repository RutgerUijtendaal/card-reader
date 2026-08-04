import { api } from '@/shared/api/client';
import type { ReviewSummaryResponse } from '@/domain/review/types';

export const fetchReviewSummary = async (): Promise<ReviewSummaryResponse> => {
  const response = await api.get<ReviewSummaryResponse>('/review/summary');
  return response.data;
};

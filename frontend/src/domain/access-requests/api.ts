import { api } from '@/shared/api/client';
import type { AccessRequestSummaryResponse } from '@/domain/access-requests/types';

export const fetchAccessRequestSummary = async (): Promise<AccessRequestSummaryResponse> => {
  const response = await api.get<AccessRequestSummaryResponse>('/admin/access-requests/summary');
  return response.data;
};

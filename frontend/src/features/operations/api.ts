import { api } from '@/shared/api/client';
import type { OperationsOverview } from '@/features/operations/types';

export const fetchOperationsOverview = async (): Promise<OperationsOverview> => {
  const response = await api.get<OperationsOverview>('/operations?include_items=false');
  return response.data;
};

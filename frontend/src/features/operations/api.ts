import { api, toAbsoluteApiUrl } from '@/shared/api/client';
import type { OperationsOverview } from '@/features/operations/types';

export const fetchOperationsOverview = async (): Promise<OperationsOverview> => {
  const response = await api.get<OperationsOverview>('/operations');
  return response.data;
};

export const operationsLinkUrl = (href: string): string => toAbsoluteApiUrl(href);

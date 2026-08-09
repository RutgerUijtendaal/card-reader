import { api, toAbsoluteApiUrl } from '@/shared/api/client';
import type { OperationsOverview, OperationsQueuePage } from '@/features/operations/types';

export const fetchOperationsOverview = async (): Promise<OperationsOverview> => {
  const response = await api.get<OperationsOverview>('/operations?include_items=false');
  return response.data;
};

export const fetchOperationsQueuePage = async (
  queueKey: string,
  page: number,
  pageSize: number,
): Promise<OperationsQueuePage> => {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  const response = await api.get<OperationsQueuePage>(
    `/operations/queues/${encodeURIComponent(queueKey)}?${params.toString()}`,
  );
  return response.data;
};

export const operationsLinkUrl = (href: string): string => toAbsoluteApiUrl(href);

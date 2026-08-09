import { api, toAbsoluteApiUrl } from '@/shared/api/client';
import type { OperationsQueuePage } from '@/domain/operations/types';

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

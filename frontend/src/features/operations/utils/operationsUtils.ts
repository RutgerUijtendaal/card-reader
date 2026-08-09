import type { OperationsItemStatus, OperationsQueueItem } from '@/domain/operations/types';
import type { OperationsQueue, WorkerOverview } from '@/features/operations/types';

const STATUS_ORDER: OperationsItemStatus[] = [
  'running',
  'canceling',
  'retrying',
  'queued',
  'scheduled',
  'failed',
  'cancelled',
  'completed',
];

export const operationsStatusEntries = (
  queue: OperationsQueue,
): Array<{ status: OperationsItemStatus; count: number }> =>
  STATUS_ORDER.flatMap((status) => {
    const count = queue.status_counts[status] ?? 0;
    return count > 0 ? [{ status, count }] : [];
  });

const ATTENTION_STATUSES: OperationsItemStatus[] = [
  'scheduled',
  'queued',
  'running',
  'canceling',
  'retrying',
  'failed',
];

export const defaultOperationsQueueKey = (queues: OperationsQueue[]): string | null => {
  const attentionQueue = queues.find((queue) =>
    ATTENTION_STATUSES.some((status) => (queue.status_counts[status] ?? 0) > 0),
  );
  return (
    attentionQueue?.key ??
    queues.find((queue) => queue.total_count > 0)?.key ??
    queues[0]?.key ??
    null
  );
};

export const operationsStatusClass = (status: OperationsItemStatus): string => {
  if (status === 'completed') return 'theme-pill-success';
  if (status === 'failed') return 'theme-pill-danger';
  if (status === 'running' || status === 'canceling' || status === 'retrying') {
    return 'theme-pill-warning';
  }
  return 'theme-pill-neutral';
};
type WorkerStatusSource = Pick<WorkerOverview, 'health' | 'activity'>;

export const workerHealthClass = (worker: WorkerStatusSource): string => {
  if (worker.health === 'online' && worker.activity === 'busy') return 'theme-pill-warning';
  if (worker.health === 'online') return 'theme-pill-success';
  if (worker.health === 'stale') return 'theme-pill-danger';
  return 'theme-pill-neutral';
};

export const workerStatusLabel = (worker: WorkerStatusSource): string => {
  if (worker.health === 'online')
    return worker.activity === 'busy' ? 'Online · Busy' : 'Online · Idle';
  if (worker.health === 'never_seen') return 'Never seen';
  return worker.health === 'stale' ? 'Offline · Stale' : 'Stopped';
};

export const operationsProgressPercent = (item: OperationsQueueItem): number | null => {
  if (item.progress_current === null || item.progress_total === null || item.progress_total <= 0) {
    return null;
  }
  return Math.max(
    0,
    Math.min(100, Math.round((item.progress_current / item.progress_total) * 100)),
  );
};

export const operationsPageCount = (count: number, pageSize: number): number =>
  pageSize > 0 ? Math.max(1, Math.ceil(count / pageSize)) : 1;

export const parseOperationsPage = (value: unknown): number => {
  const rawValue = Array.isArray(value) ? value[0] : value;
  const parsed = typeof rawValue === 'string' ? Number.parseInt(rawValue, 10) : Number.NaN;
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
};

export const formatOperationsTimestamp = (value: string | null): string => {
  if (!value) return 'Never';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

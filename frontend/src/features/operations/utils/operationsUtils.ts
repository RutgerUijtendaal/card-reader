import type {
  OperationsItemStatus,
  OperationsQueue,
  OperationsQueueItem,
  WorkerOverview,
} from '@/features/operations/types';

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

export const operationsStatusClass = (status: OperationsItemStatus): string => {
  if (status === 'completed') return 'theme-pill-success';
  if (status === 'failed') return 'theme-pill-danger';
  if (status === 'running' || status === 'canceling' || status === 'retrying') {
    return 'theme-pill-warning';
  }
  return 'theme-pill-neutral';
};
export const workerHealthClass = (worker: WorkerOverview): string => {
  if (worker.health === 'online' && worker.activity === 'busy') return 'theme-pill-warning';
  if (worker.health === 'online') return 'theme-pill-success';
  if (worker.health === 'stale') return 'theme-pill-danger';
  return 'theme-pill-neutral';
};

export const workerStatusLabel = (worker: WorkerOverview): string => {
  if (worker.health === 'online') return worker.activity === 'busy' ? 'Online · Busy' : 'Online · Idle';
  if (worker.health === 'never_seen') return 'Never seen';
  return worker.health === 'stale' ? 'Offline · Stale' : 'Stopped';
};

export const operationsProgressPercent = (item: OperationsQueueItem): number | null => {
  if (item.progress_current === null || item.progress_total === null || item.progress_total <= 0) {
    return null;
  }
  return Math.max(0, Math.min(100, Math.round((item.progress_current / item.progress_total) * 100)));
};

export const formatOperationsTimestamp = (value: string | null): string => {
  if (!value) return 'Never';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

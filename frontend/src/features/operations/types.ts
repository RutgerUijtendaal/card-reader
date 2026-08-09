import type { OperationsItemStatus, OperationsQueueItem } from '@/domain/operations/types';

export type WorkerHealth = 'online' | 'stale' | 'stopped' | 'never_seen';
export type WorkerActivity = 'idle' | 'busy' | 'stopped';

export type WorkerInstanceOverview = {
  id: string;
  display_name: string;
  health: Exclude<WorkerHealth, 'never_seen'>;
  activity: WorkerActivity;
  started_at: string;
  last_seen_at: string;
  stopped_at: string | null;
  current_work_id: string | null;
};

export type WorkerOverview = {
  key: string;
  display_name: string;
  queue_key: string;
  health: WorkerHealth;
  activity: WorkerActivity;
  active_instances: number;
  last_seen_at: string | null;
  current_work_ids: string[];
  instances: WorkerInstanceOverview[];
};
export type OperationsQueue = {
  key: string;
  display_name: string;
  worker_key: string;
  total_count: number;
  status_counts: Record<OperationsItemStatus, number>;
  items: OperationsQueueItem[];
};

export type OperationsOverview = {
  generated_at: string;
  stale_after_seconds: number;
  workers: WorkerOverview[];
  queues: OperationsQueue[];
};

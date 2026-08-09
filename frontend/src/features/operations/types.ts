export type WorkerHealth = 'online' | 'stale' | 'stopped' | 'never_seen';
export type WorkerActivity = 'idle' | 'busy' | 'stopped';
export type OperationsItemStatus =
  | 'scheduled'
  | 'queued'
  | 'running'
  | 'canceling'
  | 'retrying'
  | 'completed'
  | 'failed'
  | 'cancelled';

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
export type OperationsItemMetadata = {
  label: string;
  value: string;
};

export type OperationsItemLink = {
  label: string;
  href: string;
};

export type OperationsQueueItem = {
  id: string;
  title: string;
  status: OperationsItemStatus;
  native_status: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  progress_current: number | null;
  progress_total: number | null;
  error_message: string | null;
  metadata: OperationsItemMetadata[];
  links: OperationsItemLink[];
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

export type OperationsQueuePage = {
  count: number;
  next_page: number | null;
  previous_page: number | null;
  page: number;
  page_size: number;
  results: OperationsQueueItem[];
};

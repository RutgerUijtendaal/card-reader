export type OperationsItemStatus =
  | 'scheduled'
  | 'queued'
  | 'running'
  | 'canceling'
  | 'retrying'
  | 'completed'
  | 'failed'
  | 'cancelled';

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

export type OperationsQueuePage = {
  count: number;
  next_page: number | null;
  previous_page: number | null;
  page: number;
  page_size: number;
  results: OperationsQueueItem[];
};

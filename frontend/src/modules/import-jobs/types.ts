export type ImportJobStatus = 'queued' | 'running' | 'canceling' | 'cancelled' | 'completed' | 'failed';

export type ImportJob = {
  id: string;
  source_path: string;
  template_id: string;
  status: ImportJobStatus;
  total_items: number;
  processed_items: number;
  created_at: string;
  updated_at: string;
};

export type ImportJobItem = {
  id: string;
  source_file: string;
  status: ImportJobStatus;
  error_message: string | null;
  warning_code: string | null;
  warning_message: string | null;
};

export type ImportJobDetail = ImportJob & {
  items: ImportJobItem[];
};

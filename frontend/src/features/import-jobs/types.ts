import type { CardRole } from '@/domain/cards/cardRoles';

export type ImportJobStatus = 'queued' | 'running' | 'canceling' | 'cancelled' | 'completed' | 'failed';

export type ContentVersion = {
  id: string;
  version_number: string;
  base_version: string;
  description: string;
};

export type ImportJob = {
  id: string;
  source_path: string;
  template_id: string;
  content_version: ContentVersion | null;
  status: ImportJobStatus;
  total_items: number;
  processed_items: number;
  created_at: string;
  updated_at: string;
  card_pool: 'player' | 'game_master';
  card_role_mode: 'automatic' | 'override';
  card_role_override: CardRole[];
  template_role_snapshot: CardRole[];
  card_role_inference_policy_version: number;
};

export type ImportWarning = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export type ImportJobItem = {
  id: string;
  source_file: string;
  status: ImportJobStatus;
  error_message: string | null;
  warning_code: string | null;
  warning_message: string | null;
  warnings: ImportWarning[];
  resolved_card_roles: CardRole[];
  card_role_inference: Record<string, unknown>;
  target_card_id: string | null;
  target_card_version_id: string | null;
  target_card_pool_snapshot: 'player' | 'game_master' | null;
  target_card_roles_snapshot: CardRole[];
  card_tab_url: string | null;
};

export type ImportJobDetail = ImportJob & {
  items: ImportJobItem[];
};

export type CreateImportJobResponse = ImportJob & {
  job_id: string;
  idempotent_replay: boolean;
};

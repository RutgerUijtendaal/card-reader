import type { ContentVersion, ImportJob, ImportJobStatus } from '@/modules/import-jobs/types';

const CONTENT_VERSION_BASE_PATTERN = /^\d+\.\d+$/;

export const canCancelImportJob = (job: ImportJob): boolean =>
  job.status === 'queued' || job.status === 'running';

export const hasActiveImportJobs = (jobs: ImportJob[]): boolean =>
  jobs.some((job) => job.status === 'queued' || job.status === 'running' || job.status === 'canceling');

export const getImportJobProgressPercent = (job: ImportJob): number => {
  if (job.total_items <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((job.processed_items / job.total_items) * 100)));
};

export const getImportJobStatusClass = (status: ImportJobStatus): string => {
  if (status === 'queued') return 'theme-pill-neutral';
  if (status === 'running') return 'theme-pill-warning';
  if (status === 'canceling') return 'theme-pill-warning';
  if (status === 'cancelled') return 'theme-pill-neutral';
  if (status === 'completed') return 'theme-pill-success';
  return 'theme-pill-danger';
};

export const getImportJobProgressClass = (status: ImportJobStatus): string => {
  if (status === 'failed') return 'bg-rose-500';
  if (status === 'cancelled' || status === 'canceling') return 'bg-amber-500';
  if (status === 'completed') return 'bg-emerald-500';
  return 'bg-slate-500';
};

export const formatImportJobTimestamp = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

export const getImportSubmitLabel = (contentVersionBase: string, currentVersion: ContentVersion | null): string => {
  if (currentVersion && contentVersionBase.trim() === currentVersion.base_version) {
    return 'Update Version';
  }
  return 'Create Version';
};

export const getContentVersionBaseError = (value: string): string => {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return 'Enter a version.';
  }
  if (!CONTENT_VERSION_BASE_PATTERN.test(trimmed)) {
    return 'Use major.minor format, for example 14.1.';
  }
  return '';
};

export const getContentVersionBasePrefill = (currentVersion: ContentVersion | null): string =>
  currentVersion?.base_version ?? '';

export const getContentVersionDescriptionPrefill = (currentVersion: ContentVersion | null): string =>
  currentVersion?.description ?? '';

export const extractImportJobErrorMessage = (error: unknown): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown }; status?: number } }).response;
    const detail = maybeResponse?.data?.detail;

    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((entry) => {
          if (typeof entry === 'string') return entry;
          if (entry && typeof entry === 'object' && 'msg' in entry) {
            return String((entry as { msg: unknown }).msg);
          }
          return JSON.stringify(entry);
        })
        .join('; ');
    }

    if (detail && typeof detail === 'object') {
      return JSON.stringify(detail);
    }

    if (maybeResponse?.status) {
      return `Request failed (HTTP ${maybeResponse.status}).`;
    }
  }

  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }

  return 'Import request failed.';
};

export type DeveloperDataBundle = {
  available: true;
  bundle_version: string;
  format_version: number;
  sha256: string;
  size_bytes: number;
  created_at: string;
  download_url: string;
};

export type DeveloperDataUnavailable = {
  available: false;
  detail?: string;
};

export type DeveloperDataCurrent = DeveloperDataBundle | DeveloperDataUnavailable;

export type DeveloperDataGrant = {
  code: string;
  expires_at: string;
};

export type DeveloperDataBuildStatus = 'queued' | 'running' | 'succeeded' | 'failed';

export type DeveloperDataBuild = {
  id: string;
  bundle_version: string;
  status: DeveloperDataBuildStatus;
  requested_by: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  format_version: number | null;
  sha256: string | null;
  size_bytes: number | null;
  error_message: string | null;
  lock_download_url: string | null;
};

export type DeveloperDataBuildList = {
  builds: DeveloperDataBuild[];
};

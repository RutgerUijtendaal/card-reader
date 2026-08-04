import { api } from '@/shared/api/client';
import type { MaintenanceActionResponse } from '@/domain/maintenance/types';

const runMaintenanceAction = async (
  path: string,
  payload?: Record<string, unknown>,
): Promise<MaintenanceActionResponse> => {
  const response = payload
    ? await api.post<MaintenanceActionResponse>(path, payload)
    : await api.post<MaintenanceActionResponse>(path);
  return response.data;
};

export const queueFilteredLatestReparse = (
  payload: Record<string, unknown>,
): Promise<MaintenanceActionResponse> =>
  runMaintenanceAction('/admin/maintenance/queue-filtered-latest-reparse', payload);

export const queueLatestReparse = (): Promise<MaintenanceActionResponse> =>
  runMaintenanceAction('/admin/maintenance/queue-latest-reparse');

export const backfillMetadataSuggestions = (): Promise<MaintenanceActionResponse> =>
  runMaintenanceAction('/admin/maintenance/backfill-metadata-suggestions');

export const convertCardImagesToWebp = (): Promise<MaintenanceActionResponse> =>
  runMaintenanceAction('/admin/maintenance/convert-card-images-to-webp');

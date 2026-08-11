import { api } from '@/shared/api/client';
import type { CardRole } from '@/domain/cards/cardRoles';
import type { CardPool } from '@/domain/cards/types/cardModels';
import type {
  ContentVersion,
  CreateImportJobResponse,
  ImportJob,
  ImportJobDetail,
} from '@/features/import-jobs/types';

export const fetchImportJobs = async (): Promise<ImportJob[]> => {
  const response = await api.get<ImportJob[]>('/imports', { params: { status: 'active' } });
  return response.data;
};

export const fetchCurrentContentVersion = async (): Promise<ContentVersion | null> => {
  const response = await api.get<ContentVersion | null>('/imports/current-version');
  return response.data;
};

export type CreateImportJobInput = {
  creationKey: string;
  templateId: string;
  contentVersionBase: string;
  contentVersionDescription: string;
  files: File[];
  cardPool: CardPool;
  cardRoleMode: 'automatic' | 'override';
  cardRoleOverride: CardRole[];
};

export const createImportJob = async (
  input: CreateImportJobInput,
): Promise<CreateImportJobResponse> => {
  const formData = new FormData();
  formData.append('creation_key', input.creationKey);
  formData.append('template_id', input.templateId);
  formData.append('content_version_base', input.contentVersionBase);
  formData.append('content_version_description', input.contentVersionDescription);
  formData.append('options_json', JSON.stringify({}));
  formData.append('card_pool', input.cardPool);
  formData.append('card_role_mode', input.cardRoleMode);
  formData.append('card_role_override', JSON.stringify(input.cardRoleOverride));
  input.files.forEach((file) => formData.append('files', file));

  const response = await api.post<CreateImportJobResponse>('/imports/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const fetchImportJobByCreationKey = async (
  creationKey: string,
): Promise<CreateImportJobResponse | null> => {
  try {
    const response = await api.get<CreateImportJobResponse>(
      `/imports/by-creation-key/${creationKey}`,
    );
    return response.data;
  } catch (error: unknown) {
    if (typeof error === 'object' && error !== null && 'response' in error) {
      const response = (error as { response?: { status?: number } }).response;
      if (response?.status === 404) return null;
    }
    throw error;
  }
};

export const fetchImportJobDetail = async (jobId: string): Promise<ImportJobDetail> => {
  const response = await api.get<ImportJobDetail>(`/imports/${jobId}`);
  return response.data;
};

export const cancelImportJob = async (jobId: string): Promise<void> => {
  await api.post(`/imports/${jobId}/cancel`);
};

import { api } from '@/api/client';
import type { ContentVersion, ImportJob } from '@/modules/import-jobs/types';

export const fetchImportJobs = async (): Promise<ImportJob[]> => {
  const response = await api.get<ImportJob[]>('/imports');
  return response.data;
};

export const fetchCurrentContentVersion = async (): Promise<ContentVersion | null> => {
  const response = await api.get<ContentVersion | null>('/imports/current-version');
  return response.data;
};

export type CreateImportJobInput = {
  templateId: string;
  contentVersionBase: string;
  contentVersionDescription: string;
  files: File[];
};

export const createImportJob = async (input: CreateImportJobInput): Promise<void> => {
  const formData = new FormData();
  formData.append('template_id', input.templateId);
  formData.append('content_version_base', input.contentVersionBase);
  formData.append('content_version_description', input.contentVersionDescription);
  formData.append('options_json', JSON.stringify({}));
  input.files.forEach((file) => formData.append('files', file));

  await api.post('/imports/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const cancelImportJob = async (jobId: string): Promise<void> => {
  await api.post(`/imports/${jobId}/cancel`);
};

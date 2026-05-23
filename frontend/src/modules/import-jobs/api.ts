import { api } from '@/api/client';
import type { ImportJob } from '@/modules/import-jobs/types';

export const fetchImportJobs = async (): Promise<ImportJob[]> => {
  const response = await api.get<ImportJob[]>('/imports');
  return response.data;
};

export const createImportJob = async (templateId: string, files: File[]): Promise<void> => {
  const formData = new FormData();
  formData.append('template_id', templateId);
  formData.append('options_json', JSON.stringify({}));
  files.forEach((file) => formData.append('files', file));

  await api.post('/imports/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const cancelImportJob = async (jobId: string): Promise<void> => {
  await api.post(`/imports/${jobId}/cancel`);
};

import { api } from '@/api/client';
import type { TemplateRecord, TemplateUpsertRequest } from '@/modules/settings/types';

export const fetchTemplates = async (): Promise<TemplateRecord[]> => {
  const response = await api.get<TemplateRecord[]>('/settings/templates');
  return response.data;
};

export const createTemplate = async (payload: TemplateUpsertRequest): Promise<void> => {
  await api.post('/settings/templates', payload);
};

export const updateTemplate = async (id: string, payload: TemplateUpsertRequest): Promise<void> => {
  await api.patch(`/settings/templates/${id}`, payload);
};

export const deleteTemplate = async (id: string): Promise<void> => {
  await api.delete(`/settings/templates/${id}`);
};

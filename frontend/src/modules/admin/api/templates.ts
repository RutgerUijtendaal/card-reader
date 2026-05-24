import { api } from '@/api/client';
import { normalizeTemplateRecord } from '@/modules/admin/composables/catalogAdminUtils';
import type {
  MaintenanceActionResponse,
  TemplateApiRecord,
  TemplateRecord,
  TemplateUpsertRequest,
} from '@/modules/admin/types';

export const fetchTemplates = async (): Promise<TemplateRecord[]> => {
  const response = await api.get<TemplateApiRecord[]>('/admin/templates');
  return response.data.map(normalizeTemplateRecord);
};

export const createTemplate = async (payload: TemplateUpsertRequest): Promise<void> => {
  await api.post('/admin/templates', payload);
};

export const updateTemplate = async (id: string, payload: TemplateUpsertRequest): Promise<void> => {
  await api.patch(`/admin/templates/${id}`, payload);
};

export const deleteTemplate = async (id: string): Promise<void> => {
  await api.delete(`/admin/templates/${id}`);
};

export const queueTemplateReparse = async (
  id: string,
  sourceTemplateId: string,
): Promise<MaintenanceActionResponse> => {
  const response = await api.post<MaintenanceActionResponse>(`/admin/templates/${id}/reparse`, {
    source_template_id: sourceTemplateId,
  });
  return response.data;
};

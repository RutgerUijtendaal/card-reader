import { api } from '@/shared/api/client';
import type { MaintenanceActionResponse } from '@/domain/maintenance/types';
import type { TemplateApiRecord, TemplateRecord, TemplateUpsertRequest } from '@/domain/templates/types';

const normalizeTemplateRecord = (row: TemplateApiRecord): TemplateRecord => ({
  ...row,
  definition_json: JSON.stringify(row.definition_json, null, 2),
});

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

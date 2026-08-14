import { api } from '@/shared/api/client';
import type { TemplatePreviewCardOption } from '@/features/admin/types';

type TemplatePreviewCardsResponse = {
  results: TemplatePreviewCardOption[];
};

export const fetchTemplatePreviewCards = async (
  params: Record<string, string | number | undefined>,
): Promise<TemplatePreviewCardOption[]> => {
  const response = await api.get<TemplatePreviewCardsResponse>(
    '/admin/templates/preview-cards',
    { params },
  );
  return response.data.results;
};

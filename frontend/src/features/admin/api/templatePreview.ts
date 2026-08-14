import { fetchCardPage } from '@/domain/cards/api';
import type { TemplatePreviewCardOption } from '@/features/admin/types';

export const fetchTemplatePreviewCards = async (
  params: Record<string, string | number | undefined>,
): Promise<TemplatePreviewCardOption[]> => {
  const response = await fetchCardPage<TemplatePreviewCardOption>(
    '/admin/templates/preview-cards',
    params,
  );
  return response.results;
};

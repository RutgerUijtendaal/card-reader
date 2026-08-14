import { api } from '@/shared/api/client';
import type {
  FlagStatus,
  ParseFlagPage,
  ParseFlagReviewItem,
  ReviewCard,
} from '@/features/review-queue/types';
import type { PaginatedCardsResponse } from '@/domain/cards/types';

export const fetchReviewConfidenceCards = async (
  params: URLSearchParams,
): Promise<PaginatedCardsResponse<ReviewCard>> => {
  const response = await api.get<PaginatedCardsResponse<ReviewCard>>(
    `/review/confidence-cards?${params.toString()}`,
  );
  return response.data;
};

export const fetchParseFlagPage = async (
  status: FlagStatus,
  page: number,
  pageSize: number,
): Promise<ParseFlagPage> => {
  const params = new URLSearchParams({
    status,
    page: String(page),
    page_size: String(pageSize),
  });
  const response = await api.get<ParseFlagPage>(`/review/parse-flags?${params.toString()}`);
  return response.data;
};

export const updateParseFlagItem = async (
  itemId: string,
  status: 'resolved' | 'dismissed',
): Promise<ParseFlagReviewItem> => {
  const response = await api.patch<ParseFlagReviewItem>(`/review/parse-flags/items/${itemId}`, {
    status,
  });
  return response.data;
};

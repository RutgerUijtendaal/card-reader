import { api } from '@/shared/api/client';
import type { CardFiltersResponse, CardVersionDetail, PaginatedCardsResponse } from '@/domain/cards/types';

export type CardQueryParams = Record<string, string | number | boolean | undefined>;

export const fetchCards = async <TCard>(
  params: URLSearchParams | CardQueryParams,
): Promise<PaginatedCardsResponse<TCard>> => {
  const response = params instanceof URLSearchParams
    ? await api.get<PaginatedCardsResponse<TCard>>(`/cards?${params.toString()}`)
    : await api.get<PaginatedCardsResponse<TCard>>('/cards', { params });
  return response.data;
};

export const fetchCard = async <TCard>(cardId: string): Promise<TCard> => {
  const response = await api.get<TCard>(`/cards/${cardId}`);
  return response.data;
};

export const fetchCardVersions = async (cardId: string): Promise<CardVersionDetail[]> => {
  const response = await api.get<CardVersionDetail[]>(`/cards/${cardId}/generations`);
  return response.data;
};

export const fetchCardFilters = async (): Promise<CardFiltersResponse> => {
  const response = await api.get<CardFiltersResponse>('/cards/filters');
  return response.data;
};

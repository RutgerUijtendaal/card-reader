import { api } from '@/shared/api/client';
import type {
  CardFiltersResponse,
  CardVersionDetail,
  PaginatedCardsResponse,
} from '@/domain/cards/types';
import type { CardFilterApiPayload } from '@/domain/cards/utils/filters/cardFilterRequest';
import type { CardSort } from '@/domain/cards/utils/gallery/cardSort';
import type { CardPool } from '@/domain/cards/cardPools';
import {
  mapTtsExportResponse,
  type TtsExportApiResponse,
  type TtsExportResponse,
} from '@/domain/cards/utils/ttsExportResponse';

export type CardQueryParams = Record<string, string | number | boolean | undefined>;

export type TtsCardExportSource =
  | {
      type: 'gallery';
      filters: CardFilterApiPayload & { sort: CardSort };
    }
  | {
      type: 'content_version';
      content_version_id: string;
    };

export const fetchCardPage = async <TCard>(
  endpoint: string,
  params: URLSearchParams | CardQueryParams,
): Promise<PaginatedCardsResponse<TCard>> => {
  const response =
    params instanceof URLSearchParams
      ? await api.get<PaginatedCardsResponse<TCard>>(`${endpoint}?${params.toString()}`)
      : await api.get<PaginatedCardsResponse<TCard>>(endpoint, { params });
  return response.data;
};

export const fetchCards = async <TCard>(
  params: URLSearchParams | CardQueryParams,
): Promise<PaginatedCardsResponse<TCard>> => fetchCardPage('/cards', params);

export const fetchCard = async <TCard>(cardId: string): Promise<TCard> => {
  const response = await api.get<TCard>(`/cards/${cardId}`);
  return response.data;
};

export const fetchCardVersions = async <TCardVersion = CardVersionDetail>(cardId: string): Promise<TCardVersion[]> => {
  const response = await api.get<TCardVersion[]>(`/cards/${cardId}/generations`);
  return response.data;
};

export const fetchCardFilters = async (cardPool?: CardPool): Promise<CardFiltersResponse> => {
  const response = cardPool
    ? await api.get<CardFiltersResponse>('/cards/filters', { params: { card_pool: cardPool } })
    : await api.get<CardFiltersResponse>('/cards/filters');
  return response.data;
};

export const exportTtsCards = async (source: TtsCardExportSource): Promise<TtsExportResponse> => {
  const response = await api.post<TtsExportApiResponse>('/exports/tts/cards', { source });
  return mapTtsExportResponse(response.data);
};

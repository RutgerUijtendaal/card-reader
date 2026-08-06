import { api } from '@/shared/api/client';
import type { CardFiltersResponse, CardVersionDetail, PaginatedCardsResponse } from '@/domain/cards/types';
import type { CardFilterApiPayload } from '@/domain/cards/utils/filters/cardFilterRequest';
import type { CardSort } from '@/domain/cards/utils/gallery/cardSort';

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

export type TtsCardExportResponse = {
  encodedPayload: string;
  exportedCount: number;
  skippedCount: number;
};

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

const parseCountHeader = (value: unknown): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
};

export const exportTtsCards = async (source: TtsCardExportSource): Promise<TtsCardExportResponse> => {
  const response = await api.post<string>('/exports/tts/cards', { source }, { responseType: 'text' });
  return {
    encodedPayload: response.data,
    exportedCount: parseCountHeader(response.headers['x-card-reader-exported-count']),
    skippedCount: parseCountHeader(response.headers['x-card-reader-skipped-count']),
  };
};

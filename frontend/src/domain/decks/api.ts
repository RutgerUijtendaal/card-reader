import { api } from '@/shared/api/client';
import { isAxiosError } from 'axios';
import type {
  DeckRecord,
  DeckRulesMetadata,
  DeckSummaryCursor,
  DeckSummaryRecord,
  PaginatedDeckSummariesResponse,
  DeckTagCatalog,
  DeckUpdateRequest,
  DeckUpsertRequest,
} from '@/domain/decks/types';
import {
  mapTtsExportResponse,
  type TtsExportApiResponse,
  type TtsExportResponse,
} from '@/domain/cards/utils/ttsExportResponse';

export const fetchDeckTags = async (): Promise<DeckTagCatalog> => {
  const response = await api.get<DeckTagCatalog>('/deck-tags');
  return response.data;
};

export const fetchDeckRulesMetadata = async (): Promise<DeckRulesMetadata> => {
  const response = await api.get<DeckRulesMetadata>('/decks/rules');
  return response.data;
};

export const fetchPublicDecks = async (params?: URLSearchParams): Promise<DeckRecord[]> => {
  const response = await api.get<DeckRecord[]>('/decks', { params });
  return response.data;
};

const withSummaryView = (params?: URLSearchParams): URLSearchParams => {
  const nextParams = new URLSearchParams(params);
  nextParams.set('view', 'summary');
  return nextParams;
};

const withSummaryPagination = (
  params: URLSearchParams | undefined,
  page: number,
  pageSize: number,
  snapshotAt?: string | null,
  cursor?: DeckSummaryCursor | null,
): URLSearchParams => {
  const nextParams = withSummaryView(params);
  nextParams.set('page', String(page));
  nextParams.set('page_size', String(pageSize));
  if (snapshotAt) {
    nextParams.set('snapshot_at', snapshotAt);
  }
  if (cursor) {
    nextParams.set('cursor_created_at', cursor.created_at);
    nextParams.set('cursor_id', cursor.id);
  }
  return nextParams;
};

export const fetchPublicDeckSummaries = async (
  params?: URLSearchParams,
): Promise<DeckSummaryRecord[]> => {
  const response = await api.get<DeckSummaryRecord[]>('/decks', {
    params: withSummaryView(params),
  });
  return response.data;
};

export const fetchPublicDeckSummaryPage = async (
  params: URLSearchParams | undefined,
  page: number,
  pageSize = 10,
  snapshotAt?: string | null,
  cursor?: DeckSummaryCursor | null,
): Promise<PaginatedDeckSummariesResponse> => {
  const response = await api.get<PaginatedDeckSummariesResponse>('/decks', {
    params: withSummaryPagination(params, page, pageSize, snapshotAt, cursor),
  });
  return response.data;
};

export const fetchDeckDetail = async (deckId: string): Promise<DeckRecord> => {
  const response = await api.get<DeckRecord>(`/decks/${deckId}`);
  return response.data;
};

export const fetchMyDecks = async (params?: URLSearchParams): Promise<DeckRecord[]> => {
  const response = await api.get<DeckRecord[]>('/my/decks', { params });
  return response.data;
};

export const fetchMyDeckSummaries = async (
  params?: URLSearchParams,
): Promise<DeckSummaryRecord[]> => {
  const response = await api.get<DeckSummaryRecord[]>('/my/decks', {
    params: withSummaryView(params),
  });
  return response.data;
};

export const fetchMyDeckSummaryPage = async (
  params: URLSearchParams | undefined,
  page: number,
  pageSize = 10,
  snapshotAt?: string | null,
  cursor?: DeckSummaryCursor | null,
): Promise<PaginatedDeckSummariesResponse> => {
  const response = await api.get<PaginatedDeckSummariesResponse>('/my/decks', {
    params: withSummaryPagination(params, page, pageSize, snapshotAt, cursor),
  });
  return response.data;
};

export const fetchMyDeck = async (deckId: string): Promise<DeckRecord> => {
  const response = await api.get<DeckRecord>(`/my/decks/${deckId}`);
  return response.data;
};

export type DeckCreationResult = {
  record: DeckRecord;
  replayed: boolean;
};

export const createDeck = async (
  payload: DeckUpsertRequest,
  creationKey?: string,
): Promise<DeckCreationResult> => {
  const response = await api.post<DeckRecord>('/my/decks', payload, {
    headers: creationKey ? { 'Idempotency-Key': creationKey } : undefined,
  });
  return { record: response.data, replayed: response.status === 200 };
};

export const fetchMyDeckByCreationKey = async (
  creationKey: string,
): Promise<
  | { status: 'found'; record: DeckRecord }
  | { status: 'deleted' }
  | { status: 'missing' }
> => {
  try {
    const response = await api.get<DeckRecord>(`/my/decks/by-creation-key/${creationKey}`);
    return { status: 'found', record: response.data };
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) return { status: 'missing' };
    if (isAxiosError(error) && error.response?.status === 410) return { status: 'deleted' };
    throw error;
  }
};

export const updateDeck = async (
  deckId: string,
  payload: DeckUpdateRequest,
): Promise<DeckRecord> => {
  const response = await api.patch<DeckRecord>(`/my/decks/${deckId}`, payload);
  return response.data;
};

export const deleteDeck = async (deckId: string): Promise<void> => {
  await api.delete(`/my/decks/${deckId}`);
};

export const exportDeckTts = async (
  deckId: string,
  sideboardId?: string,
): Promise<TtsExportResponse> => {
  const params = sideboardId ? { sideboard_id: sideboardId } : undefined;
  const response = await api.get<TtsExportApiResponse>(`/decks/${deckId}/exports/tts`, { params });
  return mapTtsExportResponse(response.data);
};

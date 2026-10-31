import { isAxiosError } from 'axios';
import { api } from '@/shared/api/client';
import type { EncounterDraft, EncounterPage, EncounterRecord } from './types';
import {
  mapTtsExportResponse,
  type TtsExportApiResponse,
} from '@/domain/cards/utils/ttsExportResponse';
import type { PaginatedCardsResponse, GalleryItem } from '@/domain/cards/types';

export const fetchEncounterBosses = async (params: URLSearchParams) =>
  (await api.get<PaginatedCardsResponse<GalleryItem>>('/staff/encounters/bosses', { params })).data;

export const fetchEncounters = async (
  staff: boolean,
  params: URLSearchParams,
): Promise<EncounterPage> =>
  (await api.get<EncounterPage>(staff ? '/staff/encounters' : '/encounters', { params })).data;
export const fetchEncounter = async (id: string, staff = true): Promise<EncounterRecord> =>
  (await api.get<EncounterRecord>(`${staff ? '/staff' : ''}/encounters/${id}`)).data;
const writePayload = (payload: EncounterDraft) => ({
  ...payload,
  // Existing immutable attempts from before sideboards were supported omit this field.
  ...(payload.sideboards
    ? {
        sideboards: payload.sideboards.map((board) => ({
          ...(board.source_id ? { id: board.source_id } : {}),
          name: board.name,
          entries: board.entries,
        })),
      }
    : {}),
});
export const createEncounter = async (payload: EncounterDraft, key: string) => ({
  record: (
    await api.post<EncounterRecord>('/staff/encounters', writePayload(payload), {
      headers: { 'Idempotency-Key': key },
    })
  ).data,
});
export const lookupEncounterCreation = async (
  key: string,
): Promise<{ status: 'found'; record: EncounterRecord } | { status: 'missing' | 'deleted' }> => {
  try {
    return {
      status: 'found',
      record: (await api.get<EncounterRecord>(`/staff/encounters/by-creation-key/${key}`)).data,
    };
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) return { status: 'missing' };
    if (isAxiosError(error) && error.response?.status === 410) return { status: 'deleted' };
    throw error;
  }
};
export const updateEncounter = async (
  id: string,
  payload: EncounterDraft,
  revision: number,
): Promise<EncounterRecord> =>
  (
    await api.patch<EncounterRecord>(`/staff/encounters/${id}`, {
      ...writePayload(payload),
      revision,
    })
  ).data;
export const deleteEncounter = async (id: string, revision: number): Promise<void> => {
  await api.delete(`/staff/encounters/${id}`, { headers: { 'If-Match': String(revision) } });
};
export const fetchEncounterRules = async (): Promise<{ minimum_cards: number }> =>
  (await api.get<{ minimum_cards: number }>('/encounters/rules')).data;
export const exportEncounter = async (id: string, sideboardId?: string) =>
  mapTtsExportResponse(
    (
      await api.get<TtsExportApiResponse>(`/encounters/${id}/exports/tts`, {
        params: sideboardId ? { sideboard_id: sideboardId } : undefined,
      })
    ).data,
  );

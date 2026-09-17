import { api } from '@/shared/api/client';
import type { CardPool } from '@/domain/cards/cardPools';
import type {
  CardBackCurrentResponse,
  CardBackImportAttempt,
  CardBackImportResult,
  CardBackDefaults,
  CardBackFactionDefaults,
  CardBackRecord,
  CardBackRoleDefaults,
} from '@/domain/card-backs/types';
import type { CardFaction } from '@/domain/cards/cardFactions';
import type { CardRole } from '@/domain/cards/cardRoles';

export const importCardBack = async (attempt: CardBackImportAttempt): Promise<CardBackImportResult> => {
  const data = new FormData();
  data.append('client_request_id', attempt.clientRequestId);
  data.append('file', attempt.file);
  data.append('label', attempt.label);
  if (attempt.heroCardId !== null) {
    data.append('hero_card_id', attempt.heroCardId);
    data.append('expected_override_id', attempt.expectedOverrideId ?? '');
  }
  const response = await api.post<CardBackImportResult>('/admin/card-backs/import-items', data, { timeout: 60_000 });
  return response.data;
};

export const fetchCardBackImportResult = async (requestId: string): Promise<CardBackImportResult> => {
  const response = await api.get<CardBackImportResult>(`/admin/card-backs/import-items/${requestId}`, { timeout: 15_000 });
  return response.data;
};

export const fetchCurrentCardBack = async (): Promise<CardBackCurrentResponse> => {
  const response = await api.get<CardBackCurrentResponse>('/card-backs/current');
  return response.data;
};

export const fetchCardBacks = async (): Promise<CardBackRecord[]> => {
  const response = await api.get<CardBackRecord[]>('/admin/card-backs');
  return response.data;
};

export const fetchCardBackDefaults = async (): Promise<CardBackDefaults> => {
  const response = await api.get<CardBackDefaults>('/card-backs/defaults');
  return response.data;
};

export const fetchCardBackFactionDefaults = async (): Promise<CardBackFactionDefaults> => {
  const response = await api.get<CardBackFactionDefaults>('/card-backs/faction-defaults');
  return response.data;
};

export const fetchCardBackRoleDefaults = async (): Promise<CardBackRoleDefaults> => {
  const response = await api.get<CardBackRoleDefaults>('/card-backs/role-defaults');
  return response.data;
};

export const uploadCardBack = async (file: File, label: string): Promise<CardBackRecord> => {
  const formData = new FormData();
  formData.append('file', file);
  const normalizedLabel = label.trim();
  if (normalizedLabel.length > 0) {
    formData.append('label', normalizedLabel);
  }
  const response = await api.post<CardBackRecord>('/admin/card-backs/upload', formData);
  return response.data;
};

export const setPoolCardBackDefault = async (
  cardPool: CardPool,
  cardBackId: string | null,
): Promise<void> => {
  await api.put(`/admin/card-backs/defaults/${cardPool}`, {
    card_back_id: cardBackId,
  });
};

export const setFactionCardBackDefault = async (
  faction: CardFaction,
  cardBackId: string | null,
): Promise<void> => {
  await api.put(`/admin/card-backs/faction-defaults/${faction}`, {
    card_back_id: cardBackId,
  });
};

export const setRoleCardBackDefault = async (
  role: CardRole,
  cardBackId: string | null,
): Promise<void> => {
  await api.put(`/admin/card-backs/role-defaults/${role}`, {
    card_back_id: cardBackId,
  });
};

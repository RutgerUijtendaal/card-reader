import { api } from '@/shared/api/client';
import type { CardPool } from '@/domain/cards/cardPools';
import type {
  CardBackCurrentResponse,
  CardBackDefaults,
  CardBackFactionDefaults,
  CardBackRecord,
  CardBackRoleDefaults,
} from '@/domain/card-backs/types';
import type { CardFaction } from '@/domain/cards/cardFactions';
import type { CardRole } from '@/domain/cards/cardRoles';

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

import { api } from '@/shared/api/client';
import type { CardGroupRecord } from '@/features/admin/types';

export type CardGroupWritePayload = {
  name: string;
  anchor_card_id: string;
  members: { card_id: string; position: number }[];
};

export const fetchManagedCardGroups = async (): Promise<CardGroupRecord[]> => {
  const response = await api.get<CardGroupRecord[]>('/admin/card-groups');
  return response.data;
};

export const createManagedCardGroup = async (
  payload: CardGroupWritePayload,
): Promise<CardGroupRecord> => {
  const response = await api.post<CardGroupRecord>('/admin/card-groups', payload);
  return response.data;
};

export const updateManagedCardGroup = async (
  groupId: string,
  payload: CardGroupWritePayload,
): Promise<CardGroupRecord> => {
  const response = await api.patch<CardGroupRecord>(`/admin/card-groups/${groupId}`, payload);
  return response.data;
};

export const deleteManagedCardGroup = async (groupId: string): Promise<void> => {
  await api.delete(`/admin/card-groups/${groupId}`);
};

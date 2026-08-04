import { api } from '@/shared/api/client';
import type { CardLifecycleApiParams } from '@/domain/cards/utils/filters/cardLifecycle';
import type { CardGroupDetail } from '@/features/card-groups/types';

export const fetchCardGroupDetail = async (
  groupId: string,
  params?: CardLifecycleApiParams,
): Promise<CardGroupDetail> => {
  const response = await api.get<CardGroupDetail>(
    `/card-groups/${groupId}`,
    params ? { params } : undefined,
  );
  return response.data;
};

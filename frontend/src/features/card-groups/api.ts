import { api } from '@/shared/api/client';
import type { CardLifecycleApiParams } from '@/domain/cards/utils/filters/cardLifecycle';
import type { CardPool } from '@/domain/cards/cardPools';
import type { CardGroupDetail } from '@/features/card-groups/types';

type CardGroupDetailApiParams = Partial<CardLifecycleApiParams> & {
  card_pool?: CardPool;
};

export const fetchCardGroupDetail = async (
  groupId: string,
  params?: CardGroupDetailApiParams,
): Promise<CardGroupDetail> => {
  const response = await api.get<CardGroupDetail>(
    `/card-groups/${groupId}`,
    params ? { params } : undefined,
  );
  return response.data;
};

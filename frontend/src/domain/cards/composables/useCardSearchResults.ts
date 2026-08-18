import { ref } from 'vue';
import { fetchCards } from '@/domain/cards/api';
import type { CardPool } from '@/domain/cards/cardPools';
import type { CardListItem } from '@/domain/cards/types';
import type { CardLifecycleFilterValue } from '@/domain/cards/utils/filters/cardLifecycle';

type CardSearchOptions = {
  cardPool?: CardPool;
  lifecycleStatus?: CardLifecycleFilterValue;
  pageSize: number;
};

export const useCardSearchResults = (getOptions: () => CardSearchOptions) => {
  const results = ref<CardListItem[]>([]);
  const searching = ref(false);
  const searchError = ref(false);
  let requestId = 0;

  const clear = (): void => {
    requestId += 1;
    results.value = [];
    searching.value = false;
    searchError.value = false;
  };

  const search = async (query: string, { allowEmpty = false } = {}): Promise<void> => {
    const term = query.trim();
    if (!term && !allowEmpty) {
      clear();
      return;
    }
    const currentRequest = ++requestId;
    const options = getOptions();
    searching.value = true;
    searchError.value = false;
    try {
      const response = await fetchCards<CardListItem>({
        q: term || undefined,
        card_pool: options.cardPool,
        lifecycle_status: options.lifecycleStatus,
        page: 1,
        page_size: options.pageSize,
      });
      if (currentRequest === requestId) {
        results.value = response.results.filter(
          (item): item is CardListItem => item.result_type === 'card',
        );
      }
    } catch {
      if (currentRequest === requestId) {
        results.value = [];
        searchError.value = true;
      }
    } finally {
      if (currentRequest === requestId) searching.value = false;
    }
  };

  return { results, searching, searchError, search, clear };
};

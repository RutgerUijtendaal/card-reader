import { computed } from 'vue';
import { useLocalStorage } from '@vueuse/core';
import { DEFAULT_CARD_SORT, type CardSort } from '@/composables/card-gallery/cardSort';

type CardSortSurface = 'gallery' | 'deckBuilder' | 'deckDetail';

type CardSortOverrideState = {
  gallery: CardSort | null;
  deckBuilder: CardSort | null;
  deckDetail: CardSort | null;
};

const DEFAULT_OVERRIDES: CardSortOverrideState = {
  gallery: null,
  deckBuilder: null,
  deckDetail: null,
};

export const useCardSortPreferences = () => {
  const storedDefaultSort = useLocalStorage<CardSort>('card-reader.default-card-sort', DEFAULT_CARD_SORT);
  const storedOverrides = useLocalStorage<CardSortOverrideState>('card-reader.card-sort-overrides', DEFAULT_OVERRIDES, {
    mergeDefaults: true,
  });

  const defaultSort = computed({
    get: () => storedDefaultSort.value,
    set: (value: CardSort) => {
      storedDefaultSort.value = value;
    },
  });

  const getOverrideSort = (surface: CardSortSurface) =>
    computed<CardSort | null>({
      get: () => storedOverrides.value[surface],
      set: (value) => {
        storedOverrides.value = {
          ...storedOverrides.value,
          [surface]: value,
        };
      },
    });

  const getEffectiveSort = (surface: CardSortSurface) =>
    computed<CardSort>(() => getOverrideSort(surface).value ?? defaultSort.value);

  return {
    defaultSort,
    getOverrideSort,
    getEffectiveSort,
  };
};

export const useCardSortSurface = (surface: CardSortSurface) => {
  const preferences = useCardSortPreferences();
  const overrideSort = preferences.getOverrideSort(surface);
  const effectiveSort = preferences.getEffectiveSort(surface);

  const setOverrideSort = (value: CardSort): void => {
    overrideSort.value = value;
  };

  const clearOverrideSort = (): void => {
    overrideSort.value = null;
  };

  return {
    defaultSort: preferences.defaultSort,
    overrideSort,
    effectiveSort,
    setOverrideSort,
    clearOverrideSort,
  };
};

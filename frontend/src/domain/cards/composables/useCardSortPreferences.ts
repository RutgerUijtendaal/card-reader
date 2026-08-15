import { computed } from 'vue';
import { useStorage } from '@vueuse/core';
import { DEFAULT_CARD_SORT, isCardSort, type CardSort } from '@/domain/cards/utils/gallery/cardSort';

type CardSortSurface = 'gallery' | 'deckBuilder' | 'deckDetail';

type CardSortOverrideState = {
  gallery: CardSort | null;
  deckBuilder: CardSort | null;
  deckDetail: CardSort | null;
};

export type CardSortPreferencesState = {
  version: 1;
  defaultSort: CardSort;
  overrides: CardSortOverrideState;
};

export const CARD_SORT_PREFERENCES_STORAGE_KEY = 'card-reader.card-sort-preferences';
export const LEGACY_DEFAULT_CARD_SORT_STORAGE_KEY = 'card-reader.default-card-sort';
export const LEGACY_CARD_SORT_OVERRIDES_STORAGE_KEY = 'card-reader.card-sort-overrides';

const createDefaultPreferences = (): CardSortPreferencesState => ({
  version: 1,
  defaultSort: DEFAULT_CARD_SORT,
  overrides: {
    gallery: null,
    deckBuilder: null,
    deckDetail: null,
  },
});

const isSortOrNull = (value: unknown): value is CardSort | null => value === null || isCardSort(value);

const isCardSortPreferencesState = (value: unknown): value is CardSortPreferencesState => {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<CardSortPreferencesState>;
  const overrides = candidate.overrides as Partial<CardSortOverrideState> | undefined;
  return candidate.version === 1
    && isCardSort(candidate.defaultSort)
    && !!overrides
    && isSortOrNull(overrides.gallery)
    && isSortOrNull(overrides.deckBuilder)
    && isSortOrNull(overrides.deckDetail);
};

const parseStoredPreferences = (value: string | null): CardSortPreferencesState | null => {
  if (!value) return null;
  try {
    const parsed: unknown = JSON.parse(value);
    return isCardSortPreferencesState(parsed) ? parsed : null;
  } catch {
    return null;
  }
};

export const migrateCardSortPreferences = (
  storage: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> | null,
): CardSortPreferencesState => {
  const defaults = createDefaultPreferences();
  if (!storage) return defaults;

  try {
    const current = parseStoredPreferences(storage.getItem(CARD_SORT_PREFERENCES_STORAGE_KEY));
    if (current) {
      try {
        storage.removeItem(LEGACY_DEFAULT_CARD_SORT_STORAGE_KEY);
        storage.removeItem(LEGACY_CARD_SORT_OVERRIDES_STORAGE_KEY);
      } catch {
        // The versioned record remains authoritative even when legacy cleanup is unavailable.
      }
      return current;
    }

    const serialized = JSON.stringify(defaults);
    storage.setItem(CARD_SORT_PREFERENCES_STORAGE_KEY, serialized);
    if (storage.getItem(CARD_SORT_PREFERENCES_STORAGE_KEY) === serialized) {
      storage.removeItem(LEGACY_DEFAULT_CARD_SORT_STORAGE_KEY);
      storage.removeItem(LEGACY_CARD_SORT_OVERRIDES_STORAGE_KEY);
    }
  } catch {
    return defaults;
  }
  return defaults;
};

const resolveLocalStorage = (): Storage | null => {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
};

export const useCardSortPreferences = () => {
  const storage = resolveLocalStorage();
  const initialPreferences = migrateCardSortPreferences(storage);
  const storedPreferences = useStorage<CardSortPreferencesState>(
    CARD_SORT_PREFERENCES_STORAGE_KEY,
    initialPreferences,
    storage ?? undefined,
    {
      writeDefaults: false,
      onError: () => undefined,
    },
  );

  const defaultSort = computed({
    get: () => storedPreferences.value.defaultSort,
    set: (value: CardSort) => {
      storedPreferences.value = {
        ...storedPreferences.value,
        defaultSort: value,
      };
    },
  });

  const getOverrideSort = (surface: CardSortSurface) =>
    computed<CardSort | null>({
      get: () => storedPreferences.value.overrides[surface],
      set: (value) => {
        storedPreferences.value = {
          ...storedPreferences.value,
          overrides: {
            ...storedPreferences.value.overrides,
            [surface]: value,
          },
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

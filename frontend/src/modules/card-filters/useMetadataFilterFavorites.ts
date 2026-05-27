import { computed } from 'vue';
import { useLocalStorage } from '@vueuse/core';

export type MetadataFavoriteGroup = 'keywords' | 'tags';

type MetadataFilterFavoritesState = Record<MetadataFavoriteGroup, string[]>;

const STORAGE_KEY = 'card-reader.filter-favourites';

const DEFAULT_FAVORITES: MetadataFilterFavoritesState = {
  keywords: [],
  tags: [],
};

const normalizeFavoriteKeys = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  return [...new Set(value.filter((entry): entry is string => typeof entry === 'string').map((entry) => entry.trim()).filter(Boolean))];
};

const normalizeFavoritesState = (value: unknown): MetadataFilterFavoritesState => {
  if (!value || typeof value !== 'object') {
    return { ...DEFAULT_FAVORITES };
  }

  const record = value as Partial<Record<MetadataFavoriteGroup, unknown>>;
  return {
    keywords: normalizeFavoriteKeys(record.keywords),
    tags: normalizeFavoriteKeys(record.tags),
  };
};

export const useMetadataFilterFavorites = () => {
  const storedFavorites = useLocalStorage<MetadataFilterFavoritesState>(STORAGE_KEY, DEFAULT_FAVORITES, {
    mergeDefaults: true,
    serializer: {
      read: (value) => {
        try {
          return normalizeFavoritesState(JSON.parse(value));
        } catch {
          return { ...DEFAULT_FAVORITES };
        }
      },
      write: (value) => JSON.stringify(normalizeFavoritesState(value)),
    },
  });

  const getFavoriteKeys = (group: MetadataFavoriteGroup) =>
    computed<string[]>({
      get: () => normalizeFavoriteKeys(storedFavorites.value[group]),
      set: (value) => {
        storedFavorites.value = {
          ...storedFavorites.value,
          [group]: normalizeFavoriteKeys(value),
        };
      },
    });

  const toggleFavorite = (group: MetadataFavoriteGroup, key: string): void => {
    const normalizedKey = key.trim();
    if (!normalizedKey) {
      return;
    }

    const currentKeys = getFavoriteKeys(group).value;
    const nextKeys = currentKeys.includes(normalizedKey)
      ? currentKeys.filter((entry) => entry !== normalizedKey)
      : [...currentKeys, normalizedKey];

    getFavoriteKeys(group).value = nextKeys;
  };

  return {
    getFavoriteKeys,
    toggleFavorite,
  };
};

import { beforeEach, describe, expect, test } from 'vitest';
import { nextTick } from 'vue';
import { useMetadataFilterFavorites } from '@/composables/card-filters/useMetadataFilterFavorites';

describe('useMetadataFilterFavorites', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('defaults to empty favourites for each metadata group', () => {
    const favorites = useMetadataFilterFavorites();

    expect(favorites.getFavoriteKeys('keywords').value).toEqual([]);
    expect(favorites.getFavoriteKeys('tags').value).toEqual([]);
  });

  test('persists favourites to localStorage', async () => {
    const favorites = useMetadataFilterFavorites();

    favorites.toggleFavorite('keywords', 'flying');
    await nextTick();

    expect(localStorage.getItem('card-reader.filter-favourites')).toBe('{"keywords":["flying"],"tags":[]}');
  });

  test('toggle add and remove works without affecting other groups', async () => {
    const favorites = useMetadataFilterFavorites();

    favorites.toggleFavorite('keywords', 'flying');
    favorites.toggleFavorite('tags', 'token');
    await nextTick();

    expect(favorites.getFavoriteKeys('keywords').value).toEqual(['flying']);
    expect(favorites.getFavoriteKeys('tags').value).toEqual(['token']);

    favorites.toggleFavorite('keywords', 'flying');
    await nextTick();

    expect(favorites.getFavoriteKeys('keywords').value).toEqual([]);
    expect(favorites.getFavoriteKeys('tags').value).toEqual(['token']);
  });

  test('ignores malformed localStorage payloads safely', () => {
    localStorage.setItem('card-reader.filter-favourites', '{not-valid-json');

    const favorites = useMetadataFilterFavorites();

    expect(favorites.getFavoriteKeys('keywords').value).toEqual([]);
    expect(favorites.getFavoriteKeys('tags').value).toEqual([]);
  });
});

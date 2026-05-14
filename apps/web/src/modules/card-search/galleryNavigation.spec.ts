import { describe, expect, test } from 'vitest';
import {
  buildCardDetailLocation,
  buildGalleryLocation,
  getGallerySnapshot,
  saveGallerySnapshot,
} from './galleryNavigation';

describe('galleryNavigation', () => {
  test('preserves gallery query when building detail links', () => {
    expect(
      buildCardDetailLocation(
        'card-123',
        {
          q: 'dragon',
          keyword_keys: ['flying', 'dragon'],
        },
        'detail',
      ),
    ).toEqual({
      path: '/cards/card-123',
      query: {
        q: 'dragon',
        keyword_keys: ['dragon', 'flying'],
      },
    });
  });

  test('falls back to the gallery root when there is no gallery query', () => {
    expect(buildGalleryLocation({})).toBe('/cards');
  });

  test('preserves gallery query when returning to the gallery', () => {
    expect(
      buildGalleryLocation({
        q: 'angel',
        affinity_symbol_keys: ['air'],
      }),
    ).toEqual({
      path: '/cards',
      query: {
        q: 'angel',
        affinity_symbol_keys: ['air'],
      },
    });
  });

  test('restores snapshots only for the matching gallery query signature', () => {
    saveGallerySnapshot(
      'q=angel',
      {
        cards: [{ id: 'card-1' }],
        count: 1,
        nextPage: null,
        page: 1,
        pageSize: 72,
      },
      420,
    );

    expect(getGallerySnapshot<{ id: string }>('q=angel')).toEqual({
      searchParams: 'q=angel',
      pageState: {
        cards: [{ id: 'card-1' }],
        count: 1,
        nextPage: null,
        page: 1,
        pageSize: 72,
      },
      scrollTop: 420,
    });
    expect(getGallerySnapshot<{ id: string }>('q=dragon')).toBeNull();
  });
});

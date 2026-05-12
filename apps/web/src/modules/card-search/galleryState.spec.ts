import { describe, expect, test } from 'vitest';
import {
  appendGalleryPage,
  createEmptyGalleryPageState,
  isLatestGalleryRequest,
  replaceGalleryPage,
} from './galleryState';
import type { PaginatedCardsResponse } from '@/modules/card-detail/types';

type TestCard = {
  id: string;
  name: string;
};

const buildResponse = (overrides: Partial<PaginatedCardsResponse<TestCard>> = {}): PaginatedCardsResponse<TestCard> => ({
  count: 3,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 2,
  results: [],
  ...overrides,
});

describe('galleryState', () => {
  test('replaces state with the first page results', () => {
    const state = replaceGalleryPage(
      buildResponse({
        next_page: 2,
        results: [
          { id: 'card-1', name: 'One' },
          { id: 'card-2', name: 'Two' },
        ],
      }),
    );

    expect(state.cards.map((card) => card.id)).toEqual(['card-1', 'card-2']);
    expect(state.count).toBe(3);
    expect(state.nextPage).toBe(2);
  });

  test('appends the next page without duplicating cards', () => {
    const initial = replaceGalleryPage(
      buildResponse({
        next_page: 2,
        results: [
          { id: 'card-1', name: 'One' },
          { id: 'card-2', name: 'Two' },
        ],
      }),
    );

    const next = appendGalleryPage(
      initial,
      buildResponse({
        page: 2,
        previous_page: 1,
        results: [
          { id: 'card-2', name: 'Two' },
          { id: 'card-3', name: 'Three' },
        ],
      }),
    );

    expect(next.cards.map((card) => card.id)).toEqual(['card-1', 'card-2', 'card-3']);
    expect(next.page).toBe(2);
  });

  test('resets to an empty state when filters restart the search', () => {
    const state = createEmptyGalleryPageState<TestCard>();

    expect(state.cards).toEqual([]);
    expect(state.count).toBe(0);
    expect(state.nextPage).toBe(1);
  });

  test('rejects stale responses using request ids', () => {
    expect(isLatestGalleryRequest(3, 4)).toBe(false);
    expect(isLatestGalleryRequest(4, 4)).toBe(true);
  });
});

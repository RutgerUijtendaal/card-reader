import { reactive } from 'vue';
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { fetchCardsMock } = vi.hoisted(() => ({
  fetchCardsMock: vi.fn(),
}));

vi.mock('@/domain/cards/api', () => ({
  fetchCards: fetchCardsMock,
}));

import {
  buildCardDetailLocation,
  buildCardGroupDetailLocation,
  buildGalleryItemLocation,
  buildGalleryLocation,
  clearGalleryNavigationState,
  getGallerySnapshot,
  saveGallerySnapshot,
  setGalleryNavigationCards,
  useGalleryCardNavigation,
} from './galleryNavigation';
import { DEFAULT_CARD_PAGE_SIZE } from './pageSize';

describe('galleryNavigation', () => {
  beforeEach(() => {
    fetchCardsMock.mockReset();
    clearGalleryNavigationState();
  });

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

  test('builds dedicated group detail links for card groups', () => {
    expect(
      buildGalleryItemLocation(
        {
          id: 'group-123',
          result_type: 'card_group',
        },
        { q: 'weapon' },
        'detail',
      ),
    ).toEqual({
      path: '/card-groups/group-123',
      query: {
        q: 'weapon',
      },
    });
  });

  test('uses the card pool as the authority for direct group detail links', () => {
    expect(
      buildCardGroupDetailLocation('group-123', {}, 'evil'),
    ).toEqual({
      path: '/card-groups/group-123',
      query: { card_pool: 'evil', return_card_pool: 'player' },
    });
    expect(
      buildCardGroupDetailLocation('group-123', {}, 'neutral'),
    ).toEqual({
      path: '/card-groups/group-123',
      query: { card_pool: 'neutral', return_card_pool: 'player' },
    });
    expect(
      buildCardGroupDetailLocation(
        'group-123',
        { card_pool: 'evil' },
        'player',
      ),
    ).toEqual({
      path: '/card-groups/group-123',
      query: { return_card_pool: 'evil' },
    });
  });

  test('preserves the source workspace when opening a linked card in another pool', () => {
    expect(
      buildCardDetailLocation(
        'card-2',
        { card_pool: 'evil', q: 'boss' },
        'detail',
        'player',
      ),
    ).toEqual({
      path: '/cards/card-2',
      query: { q: 'boss', return_card_pool: 'evil' },
    });
  });

  test('uses the originating workspace when returning from a cross-pool group', () => {
    expect(
      buildGalleryLocation({
        card_pool: 'player',
        return_card_pool: 'evil',
        q: 'linked hero',
      }),
    ).toEqual({
      path: '/cards',
      query: { card_pool: 'evil', q: 'linked hero' },
    });
    expect(
      buildGalleryLocation({
        card_pool: 'evil',
        return_card_pool: 'player',
      }),
    ).toBe('/cards');
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
        cards: [{ id: 'card-1', result_type: 'card' }],
        count: 1,
        nextPage: null,
        page: 1,
        pageSize: DEFAULT_CARD_PAGE_SIZE,
      },
      420,
    );

    expect(getGallerySnapshot<{ id: string; result_type: 'card' }>('q=angel')).toEqual({
      searchParams: 'q=angel',
      pageState: {
        cards: [{ id: 'card-1', result_type: 'card' }],
        count: 1,
        nextPage: null,
        page: 1,
        pageSize: DEFAULT_CARD_PAGE_SIZE,
      },
      scrollTop: 420,
    });
    expect(getGallerySnapshot<{ id: string; result_type: 'card' }>('q=dragon')).toBeNull();
  });

  test('discards a pending pagination response after navigation state is replaced', async () => {
    let resolveFetch: ((value: {
      results: Array<{ id: string; result_type: 'card' }>;
      count: number;
      next_page: number | null;
      page_size: number;
    }) => void) | undefined;
    fetchCardsMock.mockReturnValueOnce(new Promise((resolve) => {
      resolveFetch = resolve;
    }));
    const route = reactive({
      params: { id: 'evil-current' },
      path: '/cards/evil-current',
      query: {},
    }) as unknown as RouteLocationNormalizedLoaded;
    const push = vi.fn();
    const navigation = useGalleryCardNavigation(
      route,
      { push } as unknown as Router,
      'detail',
    );
    setGalleryNavigationCards(
      [{ id: 'evil-current', result_type: 'card' }],
      2,
      2,
      DEFAULT_CARD_PAGE_SIZE,
      'card_pool=evil',
    );

    const pendingNavigation = navigation.goToNextCard();
    await Promise.resolve();
    clearGalleryNavigationState();
    setGalleryNavigationCards(
      [
        { id: 'player-current', result_type: 'card' },
        { id: 'player-next', result_type: 'card' },
      ],
      2,
      null,
      DEFAULT_CARD_PAGE_SIZE,
      '',
    );
    route.params.id = 'player-current';
    route.path = '/cards/player-current';
    resolveFetch?.({
      results: [{ id: 'evil-next', result_type: 'card' }],
      count: 2,
      next_page: null,
      page_size: DEFAULT_CARD_PAGE_SIZE,
    });
    await pendingNavigation;

    expect(navigation.nextCardId.value).toBe('player-next');
    expect(push).not.toHaveBeenCalled();
  });
});

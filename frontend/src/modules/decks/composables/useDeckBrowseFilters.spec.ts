import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { api } from '@/api/client';
import { useDeckBrowseFilters } from '@/modules/decks/composables/useDeckBrowseFilters';

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

const mockedGet = vi.mocked(api.get);

describe('useDeckBrowseFilters', () => {
  beforeEach(() => {
    mockedGet.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  test('marks filters as loaded after a successful metadata request', async () => {
    mockedGet.mockResolvedValue({
      data: {
        keywords: [],
        tags: [],
        symbols: [],
        types: [],
      },
    });

    const controller = useDeckBrowseFilters();

    await controller.loadFilters();

    expect(controller.filtersLoaded.value).toBe(true);
  });

  test('marks filters as loaded even when the metadata request fails', async () => {
    mockedGet.mockRejectedValue(new Error('temporary failure'));

    const controller = useDeckBrowseFilters();

    await expect(controller.loadFilters()).rejects.toThrow('temporary failure');
    expect(controller.filtersLoaded.value).toBe(true);
  });

  test('resets included and excluded deck tags together', () => {
    const controller = useDeckBrowseFilters();

    controller.updateDeckTagIds(['role-1']);
    controller.updateDeckTagExcludeIds(['type-1']);
    controller.updateDeckTagMatch('all');
    controller.resetDeckTags();

    expect(controller.deckTagIds.value).toEqual([]);
    expect(controller.deckTagExcludeIds.value).toEqual([]);
    expect(controller.deckTagMatch.value).toBe('any');
  });
});

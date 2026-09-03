import { beforeEach, describe, expect, test, vi } from 'vitest';
import type { SuggestionRecord } from '@/features/admin/types';
import { useCatalogAdmin } from './useCatalogAdmin';

const {
  fetchCatalogMock,
  fetchDeckTagCatalogMock,
  fetchSuggestionDetailMock,
  rejectSuggestionMock,
  routeMock,
} = vi.hoisted(() => ({
  fetchCatalogMock: vi.fn(),
  fetchDeckTagCatalogMock: vi.fn(),
  fetchSuggestionDetailMock: vi.fn(),
  rejectSuggestionMock: vi.fn(),
  routeMock: { query: { admin_kind: 'suggested-deck-types' } } as { query: Record<string, string> },
}));

vi.mock('vue-router', () => ({
  useRoute: () => routeMock,
}));

vi.mock('@/features/admin/composables/useAdminRouteSync', () => ({
  useAdminRouteSync: () => ({ replaceAdminQuery: vi.fn() }),
}));

vi.mock('vue-sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock('@/features/admin/api/catalog', () => ({
  acceptSuggestionAsNew: vi.fn(),
  acceptSuggestionToExisting: vi.fn(),
  createCatalogEntry: vi.fn(),
  deleteCatalogEntry: vi.fn(),
  fetchCatalog: fetchCatalogMock,
  fetchDeckTagCatalog: fetchDeckTagCatalogMock,
  fetchKnownCatalogEntryDetail: vi.fn(),
  fetchSuggestionDetail: fetchSuggestionDetailMock,
  rejectSuggestion: rejectSuggestionMock,
  reopenSuggestion: vi.fn(),
  updateCatalogEntry: vi.fn(),
  uploadSymbolAsset: vi.fn(),
}));

const suggestion = (
  id: string,
  status: SuggestionRecord['status'] = 'pending',
): SuggestionRecord => ({
  id,
  kind: 'type',
  display_value: `Suggestion ${id}`,
  normalized_value: `suggestion ${id}`,
  status,
  occurrence_count: 1,
  active_occurrence_count: status === 'pending' ? 1 : 0,
  rejected_resubmission_count: 0,
  accepted_target: null,
  occurrences: [],
  linked_decks: [],
  label: `Suggestion ${id}`,
  key: `suggestion ${id}`,
});

const emptyCardCatalog = {
  known: { keywords: [], tags: [], symbols: [], types: [] },
  suggested: { tags: [], types: [] },
};

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
};

beforeEach(() => {
  vi.clearAllMocks();
  routeMock.query = { admin_kind: 'suggested-deck-types' };
  fetchCatalogMock.mockResolvedValue(emptyCardCatalog);
  fetchDeckTagCatalogMock.mockResolvedValue({
    roles: [],
    types: [],
    suggestedTypes: [suggestion('one'), suggestion('two')],
  });
  rejectSuggestionMock.mockResolvedValue(undefined);
});

describe('useCatalogAdmin', () => {
  test('sorts suggested tags by workflow status and then label', async () => {
    routeMock.query = { admin_kind: 'suggested-tags' };
    fetchCatalogMock.mockResolvedValue({
      ...emptyCardCatalog,
      suggested: {
        ...emptyCardCatalog.suggested,
        tags: [
          {
            ...suggestion('rejected'),
            kind: 'tag',
            status: 'rejected',
            label: 'Alpha',
            display_value: 'Alpha',
          },
          {
            ...suggestion('accepted'),
            kind: 'tag',
            status: 'accepted',
            label: 'Beta',
            display_value: 'Beta',
          },
          { ...suggestion('pending-zulu'), kind: 'tag', label: 'Zulu', display_value: 'Zulu' },
          { ...suggestion('pending-echo'), kind: 'tag', label: 'Echo', display_value: 'Echo' },
        ],
      },
    });
    const controller = useCatalogAdmin();

    await controller.loadCatalog();

    expect(controller.currentRows.value.map((row) => row.id)).toEqual([
      'pending-echo',
      'pending-zulu',
      'accepted',
      'rejected',
    ]);
  });

  test('ignores a stale catalog refresh that completes after a newer load', async () => {
    const staleCatalog = deferred<typeof emptyCardCatalog>();
    const staleDeckTags = deferred<{
      roles: never[];
      types: never[];
      suggestedTypes: SuggestionRecord[];
    }>();
    fetchCatalogMock
      .mockReturnValueOnce(staleCatalog.promise)
      .mockResolvedValueOnce({
        ...emptyCardCatalog,
        known: {
          ...emptyCardCatalog.known,
          tags: [{ id: 'tag-new', key: 'new', label: 'New', identifiers: [] }],
        },
      });
    fetchDeckTagCatalogMock
      .mockReturnValueOnce(staleDeckTags.promise)
      .mockResolvedValueOnce({ roles: [], types: [], suggestedTypes: [suggestion('new')] });
    const controller = useCatalogAdmin();

    const staleLoad = controller.loadCatalog();
    await controller.loadCatalog();
    staleCatalog.resolve(emptyCardCatalog);
    staleDeckTags.resolve({ roles: [], types: [], suggestedTypes: [suggestion('old')] });
    await staleLoad;

    expect(controller.catalog.tags.map((row) => row.key)).toEqual(['new']);
    expect(controller.catalog['suggested-deck-types'].map((row) => row.id)).toEqual(['new']);
  });

  test('ignores a detail response after another suggestion is selected', async () => {
    const firstDetail = deferred<SuggestionRecord>();
    const secondDetail = deferred<SuggestionRecord>();
    fetchSuggestionDetailMock.mockImplementation((_kind: string, id: string) =>
      id === 'one' ? firstDetail.promise : secondDetail.promise,
    );
    const controller = useCatalogAdmin();
    await controller.loadCatalog();

    const firstSelection = controller.selectEntry('one');
    const secondSelection = controller.selectEntry('two');
    secondDetail.resolve({ ...suggestion('two'), active_occurrence_count: 7 });
    await secondSelection;

    expect(controller.selectedSuggestionRow.value?.id).toBe('two');
    expect(controller.selectedSuggestionRow.value?.active_occurrence_count).toBe(7);

    firstDetail.resolve({ ...suggestion('one'), active_occurrence_count: 9 });
    await firstSelection;

    expect(controller.selectedSuggestionRow.value?.id).toBe('two');
    expect(controller.selectedSuggestionRow.value?.active_occurrence_count).toBe(7);
    expect(controller.suggestionDetailLoading.value).toBe(false);
  });

  test('reloads selected suggestion detail after a transition', async () => {
    fetchDeckTagCatalogMock
      .mockResolvedValueOnce({ roles: [], types: [], suggestedTypes: [suggestion('one')] })
      .mockResolvedValueOnce({
        roles: [],
        types: [],
        suggestedTypes: [suggestion('one', 'rejected')],
      });
    fetchSuggestionDetailMock
      .mockResolvedValueOnce(suggestion('one'))
      .mockResolvedValueOnce({ ...suggestion('one', 'rejected'), rejected_resubmission_count: 2 });
    const controller = useCatalogAdmin();
    await controller.loadCatalog();
    await controller.selectEntry('one');

    await controller.rejectSelectedSuggestion();

    expect(rejectSuggestionMock).toHaveBeenCalledWith('suggested-deck-types', 'one');
    expect(fetchSuggestionDetailMock).toHaveBeenCalledTimes(2);
    expect(controller.selectedSuggestionRow.value?.status).toBe('rejected');
    expect(controller.selectedSuggestionRow.value?.rejected_resubmission_count).toBe(2);
  });
});

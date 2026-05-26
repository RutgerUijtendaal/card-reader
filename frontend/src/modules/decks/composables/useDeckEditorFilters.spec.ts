import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { ref } from 'vue';
import { api } from '@/api/client';
import { useDeckEditorFilters } from '@/modules/decks/composables/useDeckEditorFilters';
import type { BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

const mockedGet = vi.mocked(api.get);

describe('useDeckEditorFilters', () => {
  beforeEach(() => {
    mockedGet.mockReset();
    localStorage.clear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  test('appends current deck card ids to gallery search params when enabled', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref(['card-b', 'card-a']),
      builderStep: ref<BuilderStep>('build'),
    });

    controller.updateQuery('mage');
    controller.setCurrentDeckOnly(true);
    const params = controller.buildSearchParams();

    expect(params.get('q')).toBe('mage');
    expect(params.getAll('card_ids')).toEqual(['card-a', 'card-b']);
  });

  test('uses an empty-deck sentinel when current deck only is enabled without cards', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref([]),
      builderStep: ref<BuilderStep>('build'),
    });

    controller.setCurrentDeckOnly(true);

    expect(controller.buildSearchParams().getAll('card_ids')).toEqual(['__deck-builder-empty__']);
  });

  test('reset clears the local current deck toggle alongside shared filters', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref(['card-a']),
      builderStep: ref<BuilderStep>('build'),
    });

    controller.updateQuery('ranger');
    controller.setCurrentDeckOnly(true);
    controller.resetFilters();

    expect(controller.query.value).toBe('');
    expect(controller.currentDeckOnly.value).toBe(false);
    expect(controller.buildSearchParams().getAll('card_ids')).toEqual([]);
  });

  test('does not append current deck card ids during setup mode', () => {
    const builderStep = ref<BuilderStep>('build');
    const controller = useDeckEditorFilters({
      deckCardIds: ref(['card-a']),
      builderStep,
    });

    controller.setCurrentDeckOnly(true);
    expect(controller.buildSearchParams().getAll('card_ids')).toEqual(['card-a']);

    builderStep.value = 'setup';
    expect(controller.buildSearchParams().getAll('card_ids')).toEqual([]);
  });

  test('reuses the same current deck card id array when membership is unchanged', () => {
    const builderStep = ref<BuilderStep>('build');
    const deckCardIds = ref(['card-a', 'card-b']);
    const controller = useDeckEditorFilters({
      deckCardIds,
      builderStep,
    });

    controller.setCurrentDeckOnly(true);
    const initialValue = controller.currentDeckCardIds.value;

    deckCardIds.value = ['card-b', 'card-a', 'card-a'];

    expect(controller.currentDeckCardIds.value).toBe(initialValue);
  });
});

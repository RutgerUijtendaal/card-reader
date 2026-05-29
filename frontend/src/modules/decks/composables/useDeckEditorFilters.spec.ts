import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { ref } from 'vue';
import { api } from '@/api/client';
import { useDeckEditorFilters } from '@/modules/decks/composables/useDeckEditorFilters';
import type { BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';
import type { CardFiltersResponse } from '@/modules/card-detail/types';
import type { DeckCardSummary } from '@/modules/decks/types';

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

const mockedGet = vi.mocked(api.get);

const buildFiltersResponse = (): CardFiltersResponse => ({
  keywords: [],
  tags: [],
  types: [],
  symbols: [
    {
      id: 'arcane-mana-id',
      key: 'arcane-mana',
      label: 'Arcane Mana',
      symbol_type: 'mana',
      text_token: '{AM}',
      asset_url: null,
    },
    {
      id: 'martial-mana-id',
      key: 'martial-mana',
      label: 'Martial Mana',
      symbol_type: 'mana',
      text_token: '{MM}',
      asset_url: null,
    },
    {
      id: 'martial-affinity-id',
      key: 'martial-affinity',
      label: 'Martial Affinity',
      symbol_type: 'affinity',
      text_token: '{AFFINITY:MARTIAL}',
      asset_url: null,
    },
  ],
});

const buildHero = (): DeckCardSummary =>
  ({
    id: 'hero-1',
    result_type: 'card',
    key: 'hero-1',
    label: 'Hero',
    is_hero: true,
    template_id: '',
    version_id: 'hero-version',
    version_number: 1,
    previous_version_id: null,
    is_latest: true,
    name: 'Hero',
    type_line: 'Hero',
    mana_cost: '',
    mana_symbols: [],
    mana_value: null,
    attack: null,
    health: null,
    rules_text: '',
    confidence: 1,
    created_at: '',
    updated_at: '',
    image_url: null,
    keywords: [],
    tags: [],
    types: [],
    symbols: [
      {
        id: 'martial-affinity-id',
        key: 'martial-affinity',
        label: 'Martial Affinity',
        linked_card_count: 1,
        symbol_type: 'affinity',
        text_token: '{AFFINITY:MARTIAL}',
        asset_url: null,
      },
    ],
  }) satisfies DeckCardSummary;

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
    expect(params.get('lifecycle_status')).toBe('all');
    expect(params.getAll('card_ids')).toEqual(['card-a', 'card-b']);
  });

  test('does not add lifecycle override when current deck only is inactive', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref(['card-a']),
      builderStep: ref<BuilderStep>('build'),
    });

    expect(controller.buildSearchParams().get('lifecycle_status')).toBeNull();
  });

  test('uses an empty-deck sentinel when current deck only is enabled without cards', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref([]),
      builderStep: ref<BuilderStep>('build'),
    });

    controller.setCurrentDeckOnly(true);

    expect(controller.buildSearchParams().get('lifecycle_status')).toBe('all');
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
    expect(controller.buildSearchParams().get('lifecycle_status')).toBe('all');

    builderStep.value = 'setup';
    expect(controller.buildSearchParams().get('lifecycle_status')).toBeNull();
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

  test('applies hero affinity mana as included mana and excludes other mana symbols', async () => {
    mockedGet.mockResolvedValue({ data: buildFiltersResponse() });
    const controller = useDeckEditorFilters({
      deckCardIds: ref([]),
      builderStep: ref<BuilderStep>('build'),
    });

    await controller.loadFilters();
    controller.updateQuery('old search');
    controller.setCurrentDeckOnly(true);
    controller.applyHeroAffinityManaPreset(buildHero());

    const params = controller.buildSearchParams();
    expect(controller.query.value).toBe('');
    expect(controller.currentDeckOnly.value).toBe(false);
    expect(params.getAll('mana_symbol_ids')).toEqual(['martial-mana-id']);
    expect(params.getAll('mana_symbol_exclude_ids')).toEqual(['arcane-mana-id']);
    expect(params.get('mana_symbol_match')).toBe('any');
  });

  test('ignores hidden mana filters while selecting a hero in setup mode', async () => {
    mockedGet.mockResolvedValue({ data: buildFiltersResponse() });
    const builderStep = ref<BuilderStep>('build');
    const controller = useDeckEditorFilters({
      deckCardIds: ref([]),
      builderStep,
    });

    await controller.loadFilters();
    controller.applyHeroAffinityManaPreset(buildHero());
    builderStep.value = 'setup';

    const params = controller.buildSearchParams();
    expect(params.getAll('mana_symbol_ids')).toEqual([]);
    expect(params.getAll('mana_symbol_exclude_ids')).toEqual([]);
    expect(params.get('mana_symbol_match')).toBeNull();
  });
});

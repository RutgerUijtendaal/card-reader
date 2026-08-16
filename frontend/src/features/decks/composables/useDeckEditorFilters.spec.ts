import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { ref } from 'vue';
import { api } from '@/shared/api/client';
import { useDeckEditorFilters } from '@/features/decks/composables/useDeckEditorFilters';
import type { DeckEditorMode } from '@/features/decks/composables/deckEditorDraftTypes';
import type { CardFiltersResponse } from '@/domain/cards/types';
import type { DeckCardSummary } from '@/domain/decks/types';

vi.mock('@/shared/api/client', () => ({
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
  mana_families: [
    {
      key: 'arcane',
      label: 'Arcane',
      rank: 0,
      mana_symbol: {
        id: 'arcane-mana-id',
        key: 'arcane-mana',
        label: 'Arcane Mana',
        symbol_type: 'mana',
        text_token: '{AM}',
        asset_url: null,
      },
      affinity_symbol: null,
    },
    {
      key: 'martial',
      label: 'Martial',
      rank: 3,
      mana_symbol: {
        id: 'martial-mana-id',
        key: 'martial-mana',
        label: 'Martial Mana',
        symbol_type: 'mana',
        text_token: '{MM}',
        asset_url: null,
      },
      affinity_symbol: {
        id: 'martial-affinity-id',
        key: 'martial-affinity',
        label: 'Martial Affinity',
        symbol_type: 'affinity',
        text_token: '{AFFINITY:MARTIAL}',
        asset_url: null,
      },
    },
  ],
});

const buildHero = (): DeckCardSummary =>
  ({
    id: 'hero-1',
    result_type: 'card',
    key: 'hero-1',
    label: 'Hero',
    card_pool: 'player' as const, card_roles: ['hero' as const],
    card_factions: [],
    card_mana_families: ['martial'],
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
      editorMode: ref<DeckEditorMode>('cards'),
    });

    controller.updateQuery('mage');
    controller.setCurrentDeckOnly(true);
    const params = controller.buildSearchParams();

    expect(params.get('q')).toBe('mage');
    expect(params.get('sort')).toBe('default');
    expect(params.get('lifecycle_status')).toBe('all');
    expect(params.getAll('card_ids')).toEqual(['card-a', 'card-b']);
  });

  test('does not add lifecycle override when current deck only is inactive', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref(['card-a']),
      editorMode: ref<DeckEditorMode>('cards'),
    });

    expect(controller.buildSearchParams().get('lifecycle_status')).toBeNull();
  });

  test('omits unsupported role and faction filters from card gallery requests', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref([]),
      editorMode: ref<DeckEditorMode>('cards'),
    });

    const sections = controller.filterSectionsState.value;
    sections.onUpdateSelectedCardRoles(['boss']);
    sections.onUpdateExcludedCardRoles(['event']);
    sections.onUpdateCardRoleMatch('all');
    sections.onUpdateSelectedCardFactions(['dark']);
    sections.onUpdateExcludedCardFactions(['blood']);
    sections.onUpdateCardFactionMatch('all');

    const params = controller.buildSearchParams();
    expect(params.has('card_roles')).toBe(false);
    expect(params.has('card_role_exclude')).toBe(false);
    expect(params.has('card_role_match')).toBe(false);
    expect(params.has('card_factions')).toBe(false);
    expect(params.has('card_faction_exclude')).toBe(false);
    expect(params.has('card_faction_match')).toBe(false);
  });

  test('uses an empty-deck sentinel when current deck only is enabled without cards', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref([]),
      editorMode: ref<DeckEditorMode>('cards'),
    });

    controller.setCurrentDeckOnly(true);

    expect(controller.buildSearchParams().get('lifecycle_status')).toBe('all');
    expect(controller.buildSearchParams().getAll('card_ids')).toEqual(['__deck-builder-empty__']);
  });

  test('reset clears the local current deck toggle alongside shared filters', () => {
    const controller = useDeckEditorFilters({
      deckCardIds: ref(['card-a']),
      editorMode: ref<DeckEditorMode>('cards'),
    });

    controller.updateQuery('ranger');
    controller.setCurrentDeckOnly(true);
    controller.resetFilters();

    expect(controller.query.value).toBe('');
    expect(controller.currentDeckOnly.value).toBe(false);
    expect(controller.buildSearchParams().getAll('card_ids')).toEqual([]);
  });

  test('does not append current deck card ids during setup mode', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const controller = useDeckEditorFilters({
      deckCardIds: ref(['card-a']),
      editorMode,
    });

    controller.setCurrentDeckOnly(true);
    expect(controller.buildSearchParams().getAll('card_ids')).toEqual(['card-a']);
    expect(controller.buildSearchParams().get('lifecycle_status')).toBe('all');

    editorMode.value = 'hero';
    expect(controller.buildSearchParams().get('lifecycle_status')).toBeNull();
    expect(controller.buildSearchParams().getAll('card_ids')).toEqual([]);
  });

  test('reuses the same current deck card id array when membership is unchanged', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const deckCardIds = ref(['card-a', 'card-b']);
    const controller = useDeckEditorFilters({
      deckCardIds,
      editorMode,
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
      editorMode: ref<DeckEditorMode>('cards'),
    });

    await controller.loadFilters();
    controller.updateQuery('old search');
    controller.setCurrentDeckOnly(true);
    controller.applyHeroManaFamilyPreset(buildHero());

    const params = controller.buildSearchParams();
    expect(controller.query.value).toBe('');
    expect(controller.currentDeckOnly.value).toBe(false);
    expect(params.getAll('mana_family_keys')).toEqual(['martial']);
    expect(params.getAll('mana_family_exclude_keys')).toEqual(['arcane']);
    expect(params.get('mana_family_match')).toBe('any');
  });

  test('keeps canonical mana-family filters while selecting a hero in setup mode', async () => {
    mockedGet.mockResolvedValue({ data: buildFiltersResponse() });
    const editorMode = ref<DeckEditorMode>('cards');
    const controller = useDeckEditorFilters({
      deckCardIds: ref([]),
      editorMode,
    });

    await controller.loadFilters();
    controller.applyHeroManaFamilyPreset(buildHero());
    editorMode.value = 'hero';

    const params = controller.buildSearchParams();
    expect(params.getAll('mana_family_keys')).toEqual(['martial']);
    expect(params.getAll('mana_family_exclude_keys')).toEqual(['arcane']);
    expect(params.get('mana_family_match')).toBe('any');
  });
});

import { describe, expect, test } from 'vitest';
import type { CardFiltersResponse } from '@/modules/card-detail/types';
import type { DeckTagCatalog } from '@/modules/decks/types';
import {
  buildDeckBrowseFilterApiSearchParams,
  buildDeckBrowseFilterSelectionState,
  buildDeckBrowseFilterStateFromSelection,
  buildDeckBrowseFilterRouteQuery,
  createDeckBrowseFilterCatalog,
  createEmptyDeckBrowseFilterState,
  parseDeckBrowseFilterRouteQuery,
} from '@/composables/decks/deckBrowseFilterState';

const filters: CardFiltersResponse = {
  keywords: [],
  tags: [],
  types: [],
  symbols: [
    { id: 'sym-1', key: 'fire', label: 'Fire', symbol_type: 'affinity', text_token: '{AF}', asset_url: null },
    { id: 'sym-2', key: 'water', label: 'Water', symbol_type: 'affinity', text_token: '{AW}', asset_url: null },
    { id: 'sym-3', key: 'mana-fire', label: 'Mana Fire', symbol_type: 'mana', text_token: '{F}', asset_url: null },
  ],
};

const deckTags: DeckTagCatalog = {
  roles: [{ id: 'role-1', kind: 'role', key: 'damage', label: 'Damage' }],
  types: [{ id: 'type-1', kind: 'type', key: 'armor', label: 'Armor' }],
};

describe('deckBrowseFilterState', () => {
  test('parses and rebuilds route query using stable keys', () => {
    const parsed = parseDeckBrowseFilterRouteQuery({
      q: '  Aurora Spear  ',
      affinity_symbol_match: 'all',
      affinity_symbol_keys: ['water', 'fire'],
      affinity_symbol_exclude_keys: ['fire'],
      deck_tag_match: 'all',
      deck_tag_keys: ['type:armor', 'role:damage'],
    });

    expect(parsed).toEqual({
      query: 'Aurora Spear',
      affinitySymbolMatch: 'all',
      affinitySymbolKeys: ['fire', 'water'],
      affinitySymbolExcludeKeys: ['fire'],
      deckTagMatch: 'all',
      deckTagKeys: ['role:damage', 'type:armor'],
    });
    expect(buildDeckBrowseFilterRouteQuery(parsed)).toEqual({
      q: 'Aurora Spear',
      affinity_symbol_match: 'all',
      affinity_symbol_keys: ['fire', 'water'],
      affinity_symbol_exclude_keys: ['fire'],
      deck_tag_match: 'all',
      deck_tag_keys: ['role:damage', 'type:armor'],
    });
  });

  test('maps route keys to selection ids and back again', () => {
    const catalog = createDeckBrowseFilterCatalog(filters, deckTags);
    const selection = buildDeckBrowseFilterSelectionState(
      {
        query: 'Aurora Spear',
        affinitySymbolMatch: 'all',
        affinitySymbolKeys: ['fire', 'water'],
        affinitySymbolExcludeKeys: ['fire'],
        deckTagMatch: 'all',
        deckTagKeys: ['role:damage', 'type:armor'],
      },
      catalog,
    );

    expect(selection).toEqual({
      query: 'Aurora Spear',
      affinitySymbolMatch: 'all',
      affinitySymbolIds: ['sym-1', 'sym-2'],
      affinitySymbolExcludeIds: ['sym-1'],
      deckTagMatch: 'all',
      deckTagIds: ['role-1', 'type-1'],
    });
    expect(buildDeckBrowseFilterStateFromSelection(selection, catalog)).toEqual({
      query: 'Aurora Spear',
      affinitySymbolMatch: 'all',
      affinitySymbolKeys: ['fire', 'water'],
      affinitySymbolExcludeKeys: ['fire'],
      deckTagMatch: 'all',
      deckTagKeys: ['role:damage', 'type:armor'],
    });
  });

  test('builds api params for text and affinity filters', () => {
    const params = buildDeckBrowseFilterApiSearchParams({
      query: 'Aurora Spear',
      affinitySymbolMatch: 'all',
      affinitySymbolIds: ['sym-1', 'sym-2'],
      affinitySymbolExcludeIds: ['sym-1'],
      deckTagMatch: 'all',
      deckTagIds: ['role-1', 'type-1'],
    });

    expect(params.get('q')).toBe('Aurora Spear');
    expect(params.get('affinity_symbol_match')).toBe('all');
    expect(params.getAll('affinity_symbol_ids')).toEqual(['sym-1', 'sym-2']);
    expect(params.getAll('affinity_symbol_exclude_ids')).toEqual(['sym-1']);
    expect(params.get('deck_tag_match')).toBe('all');
    expect(params.getAll('deck_tag_ids')).toEqual(['role-1', 'type-1']);
  });

  test('empty state clears text search and affinity selections', () => {
    expect(createEmptyDeckBrowseFilterState()).toEqual({
      query: '',
      affinitySymbolMatch: 'any',
      affinitySymbolKeys: [],
      affinitySymbolExcludeKeys: [],
      deckTagMatch: 'any',
      deckTagKeys: [],
    });
  });
});

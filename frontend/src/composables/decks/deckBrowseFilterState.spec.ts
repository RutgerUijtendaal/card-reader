import { describe, expect, test } from 'vitest';
import type { CardFiltersResponse } from '@/modules/card-detail/types';
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

describe('deckBrowseFilterState', () => {
  test('parses and rebuilds route query using stable keys', () => {
    const parsed = parseDeckBrowseFilterRouteQuery({
      hero_q: '  Aurora  ',
      author_q: '  Mina ',
      card_q: '  Spear ',
      affinity_symbol_match: 'all',
      affinity_symbol_keys: ['water', 'fire'],
      affinity_symbol_exclude_keys: ['fire'],
    });

    expect(parsed).toEqual({
      heroQuery: 'Aurora',
      authorQuery: 'Mina',
      cardQuery: 'Spear',
      affinitySymbolMatch: 'all',
      affinitySymbolKeys: ['fire', 'water'],
      affinitySymbolExcludeKeys: ['fire'],
    });
    expect(buildDeckBrowseFilterRouteQuery(parsed)).toEqual({
      hero_q: 'Aurora',
      author_q: 'Mina',
      card_q: 'Spear',
      affinity_symbol_match: 'all',
      affinity_symbol_keys: ['fire', 'water'],
      affinity_symbol_exclude_keys: ['fire'],
    });
  });

  test('maps route keys to selection ids and back again', () => {
    const catalog = createDeckBrowseFilterCatalog(filters);
    const selection = buildDeckBrowseFilterSelectionState(
      {
        heroQuery: 'Aurora',
        authorQuery: 'Mina',
        cardQuery: 'Spear',
        affinitySymbolMatch: 'all',
        affinitySymbolKeys: ['fire', 'water'],
        affinitySymbolExcludeKeys: ['fire'],
      },
      catalog,
    );

    expect(selection).toEqual({
      heroQuery: 'Aurora',
      authorQuery: 'Mina',
      cardQuery: 'Spear',
      affinitySymbolMatch: 'all',
      affinitySymbolIds: ['sym-1', 'sym-2'],
      affinitySymbolExcludeIds: ['sym-1'],
    });
    expect(buildDeckBrowseFilterStateFromSelection(selection, catalog)).toEqual({
      heroQuery: 'Aurora',
      authorQuery: 'Mina',
      cardQuery: 'Spear',
      affinitySymbolMatch: 'all',
      affinitySymbolKeys: ['fire', 'water'],
      affinitySymbolExcludeKeys: ['fire'],
    });
  });

  test('builds api params for text and affinity filters', () => {
    const params = buildDeckBrowseFilterApiSearchParams({
      heroQuery: 'Aurora',
      authorQuery: 'Mina',
      cardQuery: 'Spear',
      affinitySymbolMatch: 'all',
      affinitySymbolIds: ['sym-1', 'sym-2'],
      affinitySymbolExcludeIds: ['sym-1'],
    });

    expect(params.get('hero_q')).toBe('Aurora');
    expect(params.get('author_q')).toBe('Mina');
    expect(params.get('card_q')).toBe('Spear');
    expect(params.get('affinity_symbol_match')).toBe('all');
    expect(params.getAll('affinity_symbol_ids')).toEqual(['sym-1', 'sym-2']);
    expect(params.getAll('affinity_symbol_exclude_ids')).toEqual(['sym-1']);
  });

  test('empty state clears both text filters and affinity selections', () => {
    expect(createEmptyDeckBrowseFilterState()).toEqual({
      heroQuery: '',
      authorQuery: '',
      cardQuery: '',
      affinitySymbolMatch: 'any',
      affinitySymbolKeys: [],
      affinitySymbolExcludeKeys: [],
    });
  });
});

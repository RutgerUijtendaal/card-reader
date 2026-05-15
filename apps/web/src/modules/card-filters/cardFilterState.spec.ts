import { describe, expect, test } from 'vitest';
import {
  buildCardFilterApiSearchParams,
  buildCardFilterSelectionState,
  buildCardFilterStateFromSelection,
  createCardFilterCatalog,
} from './cardFilterState';
import type { CardFiltersResponse } from '@/modules/card-detail/types';

const filters: CardFiltersResponse = {
  keywords: [{ id: 'kw-1', key: 'flying', label: 'Flying' }],
  tags: [{ id: 'tag-1', key: 'rare', label: 'Rare' }],
  types: [{ id: 'type-1', key: 'creature', label: 'Creature' }],
  symbols: [
    { id: 'sym-1', key: 'mana-fire', label: 'Fire', symbol_type: 'mana', text_token: '{F}', asset_url: null },
    { id: 'sym-1b', key: 'colorless-mana-3', label: 'Colorless Mana 3', symbol_type: 'mana', text_token: '{3}', asset_url: null },
    { id: 'sym-2', key: 'air', label: 'Air', symbol_type: 'affinity', text_token: '{A}', asset_url: null },
    { id: 'sym-3', key: 'pray', label: 'Pray', symbol_type: 'devotion', text_token: '{P}', asset_url: null },
    { id: 'sym-4', key: 'tap', label: 'Tap', symbol_type: 'other', text_token: '{T}', asset_url: null },
  ],
};

describe('cardFilterState adapters', () => {
  test('maps route key state to UI selection ids', () => {
    const selection = buildCardFilterSelectionState(
      {
        query: 'dragon',
        keywordMatch: 'all',
        tagMatch: 'any',
        typeMatch: 'all',
        manaSymbolMatch: 'all',
        affinitySymbolMatch: 'any',
        devotionSymbolMatch: 'any',
        otherSymbolMatch: 'any',
        templateId: '',
        manaCostMin: '2',
        manaCostMax: '5',
        attackMin: '',
        attackMax: '',
        healthMin: '',
        healthMax: '',
        keywordKeys: ['flying'],
        tagKeys: ['rare'],
        manaSymbolKeys: ['mana-fire'],
        affinitySymbolKeys: ['air'],
        devotionSymbolKeys: ['pray'],
        otherSymbolKeys: ['tap'],
        typeKeys: ['creature'],
      },
      createCardFilterCatalog(filters),
    );

    expect(selection).toMatchObject({
      query: 'dragon',
      keywordMatch: 'all',
      typeMatch: 'all',
      manaSymbolMatch: 'all',
      manaCostMin: '2',
      manaCostMax: '5',
      keywordIds: ['kw-1'],
      tagIds: ['tag-1'],
      manaTypeSymbolIds: ['sym-1'],
      affinitySymbolIds: ['sym-2'],
      devotionSymbolIds: ['sym-3'],
      otherSymbolIds: ['sym-4'],
      typeIds: ['type-1'],
    });
  });

  test('maps UI selection ids back to stable route keys', () => {
    const state = buildCardFilterStateFromSelection(
      {
        query: '',
        keywordMatch: 'all',
        tagMatch: 'all',
        typeMatch: 'any',
        manaSymbolMatch: 'all',
        affinitySymbolMatch: 'all',
        devotionSymbolMatch: 'any',
        otherSymbolMatch: 'any',
        templateId: '',
        manaCostMin: '1',
        manaCostMax: '6',
        attackMin: '',
        attackMax: '',
        healthMin: '',
        healthMax: '',
        keywordIds: ['kw-1'],
        tagIds: ['tag-1'],
        manaTypeSymbolIds: ['sym-1'],
        affinitySymbolIds: ['sym-2'],
        devotionSymbolIds: ['sym-3'],
        otherSymbolIds: ['sym-4'],
        typeIds: ['type-1'],
      },
      createCardFilterCatalog(filters),
    );

    expect(state).toMatchObject({
      keywordMatch: 'all',
      tagMatch: 'all',
      manaSymbolMatch: 'all',
      affinitySymbolMatch: 'all',
      manaCostMin: '1',
      manaCostMax: '6',
      keywordKeys: ['flying'],
      tagKeys: ['rare'],
      manaSymbolKeys: ['mana-fire'],
      affinitySymbolKeys: ['air'],
      devotionSymbolKeys: ['pray'],
      otherSymbolKeys: ['tap'],
      typeKeys: ['creature'],
    });
  });

  test('builds API params with UUID ids only', () => {
    const params = buildCardFilterApiSearchParams({
      query: '',
      keywordMatch: 'all',
      tagMatch: 'all',
      typeMatch: 'any',
      manaSymbolMatch: 'all',
      affinitySymbolMatch: 'all',
      devotionSymbolMatch: 'any',
      otherSymbolMatch: 'any',
      templateId: '',
      manaCostMin: '2',
      manaCostMax: '7',
      attackMin: '',
      attackMax: '',
      healthMin: '',
      healthMax: '',
      keywordIds: ['kw-1'],
      tagIds: ['tag-1'],
      manaTypeSymbolIds: ['sym-1'],
      affinitySymbolIds: ['sym-2'],
      devotionSymbolIds: ['sym-3'],
      otherSymbolIds: ['sym-4'],
      typeIds: ['type-1'],
    });

    expect(params.getAll('keyword_ids')).toEqual(['kw-1']);
    expect(params.get('keyword_match')).toBe('all');
    expect(params.getAll('tag_ids')).toEqual(['tag-1']);
    expect(params.get('tag_match')).toBe('all');
    expect(params.getAll('mana_symbol_ids')).toEqual(['sym-1']);
    expect(params.get('mana_symbol_match')).toBe('all');
    expect(params.getAll('affinity_symbol_ids')).toEqual(['sym-2']);
    expect(params.get('affinity_symbol_match')).toBe('all');
    expect(params.getAll('devotion_symbol_ids')).toEqual(['sym-3']);
    expect(params.get('devotion_symbol_match')).toBe('any');
    expect(params.getAll('other_symbol_ids')).toEqual(['sym-4']);
    expect(params.get('other_symbol_match')).toBe('any');
    expect(params.getAll('symbol_ids')).toEqual([]);
    expect(params.getAll('type_ids')).toEqual(['type-1']);
    expect(params.get('type_match')).toBe('any');
    expect(params.get('mana_cost_min')).toBe('2');
    expect(params.get('mana_cost_max')).toBe('7');
    expect(params.getAll('keyword_keys')).toEqual([]);
  });

  test('excludes colorless mana symbols from the mana toggle catalog', () => {
    const catalog = createCardFilterCatalog(filters);

    expect(catalog.manaSymbols.map((row) => row.key)).toEqual(['mana-fire']);
  });
});

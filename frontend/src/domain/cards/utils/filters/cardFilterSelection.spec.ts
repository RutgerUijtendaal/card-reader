import { describe, expect, test } from 'vitest';
import {
  buildCardFilterSelectionState,
  buildCardFilterStateFromSelection,
  createCardFilterCatalog,
} from './cardFilterSelection';
import type { CardFiltersResponse } from '@/domain/cards/types';

const filters: CardFiltersResponse = {
  keywords: [{ id: 'kw-1', key: 'flying', label: 'Flying' }],
  tags: [{ id: 'tag-1', key: 'rare', label: 'Rare' }],
  types: [
    { id: 'type-1', key: 'creature', label: 'Creature' },
    { id: 'type-2', key: 'spell', label: 'Spell' },
  ],
  symbols: [
    {
      id: 'sym-1',
      key: 'mana-fire',
      label: 'Fire',
      symbol_type: 'mana',
      text_token: '{F}',
      asset_url: null,
    },
    {
      id: 'sym-1b',
      key: 'colorless-mana-3',
      label: 'Colorless Mana 3',
      symbol_type: 'mana',
      text_token: '{3}',
      asset_url: null,
    },
    {
      id: 'sym-2',
      key: 'air',
      label: 'Air',
      symbol_type: 'affinity',
      text_token: '{A}',
      asset_url: null,
    },
    {
      id: 'sym-3',
      key: 'pray',
      label: 'Pray',
      symbol_type: 'devotion',
      text_token: '{P}',
      asset_url: null,
    },
    {
      id: 'sym-4',
      key: 'tap',
      label: 'Tap',
      symbol_type: 'other',
      text_token: '{T}',
      asset_url: null,
    },
  ],
};

describe('cardFilterSelection', () => {
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
        manaSymbolExcludeKeys: [],
        affinitySymbolKeys: ['air'],
        affinitySymbolExcludeKeys: [],
        devotionSymbolKeys: ['pray'],
        devotionSymbolExcludeKeys: [],
        otherSymbolKeys: ['tap'],
        otherSymbolExcludeKeys: [],
        typeKeys: ['creature'],
        typeExcludeKeys: ['spell'],
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
      manaTypeSymbolExcludeIds: [],
      affinitySymbolIds: ['sym-2'],
      affinitySymbolExcludeIds: [],
      devotionSymbolIds: ['sym-3'],
      devotionSymbolExcludeIds: [],
      otherSymbolIds: ['sym-4'],
      otherSymbolExcludeIds: [],
      typeIds: ['type-1'],
      typeExcludeIds: ['type-2'],
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
        manaTypeSymbolExcludeIds: ['sym-1'],
        affinitySymbolIds: ['sym-2'],
        affinitySymbolExcludeIds: ['sym-2'],
        devotionSymbolIds: ['sym-3'],
        devotionSymbolExcludeIds: ['sym-3'],
        otherSymbolIds: ['sym-4'],
        otherSymbolExcludeIds: ['sym-4'],
        typeIds: ['type-1'],
        typeExcludeIds: ['type-2'],
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
      manaSymbolExcludeKeys: ['mana-fire'],
      affinitySymbolKeys: ['air'],
      affinitySymbolExcludeKeys: ['air'],
      devotionSymbolKeys: ['pray'],
      devotionSymbolExcludeKeys: ['pray'],
      otherSymbolKeys: ['tap'],
      otherSymbolExcludeKeys: ['tap'],
      typeKeys: ['creature'],
      typeExcludeKeys: ['spell'],
    });
  });

  test('excludes colorless mana symbols from the mana toggle catalog', () => {
    const catalog = createCardFilterCatalog(filters);

    expect(catalog.manaSymbols.map((row) => row.key)).toEqual(['mana-fire']);
  });
});

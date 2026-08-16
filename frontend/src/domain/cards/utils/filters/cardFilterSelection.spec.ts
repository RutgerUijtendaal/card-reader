import { describe, expect, test } from 'vitest';
import {
  buildCardFilterSelectionState,
  buildCardFilterStateFromSelection,
  cardFilterStateRequiresCatalog,
  createCardFilterCatalog,
  reconcileCardFilterStateWithCatalog,
} from './cardFilterSelection';
import type { CardFiltersResponse } from '@/domain/cards/types';
import { createEmptyCardFilterState } from './cardFilterState';

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
      key: 'arcane-mana',
      label: 'Arcane Mana',
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
      key: 'arcane-affinity',
      label: 'Arcane Affinity',
      symbol_type: 'affinity',
      text_token: '{A}',
      asset_url: null,
    },
    {
      id: 'sym-2b',
      key: 'sola-affinity',
      label: 'Sola Affinity',
      symbol_type: 'affinity',
      text_token: '{AFFINITY:SOLA}',
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
  mana_families: [
    {
      key: 'arcane',
      label: 'Arcane',
      rank: 0,
      mana_symbol: {
        id: 'sym-1',
        key: 'arcane-mana',
        label: 'Arcane Mana',
        symbol_type: 'mana',
        text_token: '{AM}',
        asset_url: null,
      },
      affinity_symbol: {
        id: 'sym-2',
        key: 'arcane-affinity',
        label: 'Arcane Affinity',
        symbol_type: 'affinity',
        text_token: '{AFFINITY:ARCANE}',
        asset_url: null,
      },
    },
  ],
};

describe('cardFilterSelection', () => {
  test('maps route key state to UI selection ids', () => {
    const selection = buildCardFilterSelectionState(
      {
        query: 'dragon',
        cardPool: 'player',
        cardRoleMatch: 'any',
        cardRoleKeys: [],
        cardRoleExcludeKeys: ['hero'],
        keywordMatch: 'all',
        tagMatch: 'any',
        typeMatch: 'all',
        manaFamilyMatch: 'all',
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
        manaFamilyKeys: ['arcane-mana'],
        manaFamilyExcludeKeys: [],
        affinitySymbolKeys: ['sola-affinity'],
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
      manaFamilyMatch: 'all',
      manaCostMin: '2',
      manaCostMax: '5',
      keywordIds: ['kw-1'],
      tagIds: ['tag-1'],
      manaFamilyIds: ['arcane'],
      manaFamilyExcludeIds: [],
      affinitySymbolIds: ['sym-2b'],
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
        cardPool: 'player',
        cardRoleMatch: 'any',
        cardRoleIds: [],
        cardRoleExcludeIds: ['hero'],
        keywordMatch: 'all',
        tagMatch: 'all',
        typeMatch: 'any',
        manaFamilyMatch: 'all',
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
        manaFamilyIds: ['arcane'],
        manaFamilyExcludeIds: ['arcane'],
        affinitySymbolIds: ['sym-2b'],
        affinitySymbolExcludeIds: ['sym-2b'],
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
      manaFamilyMatch: 'all',
      affinitySymbolMatch: 'all',
      manaCostMin: '1',
      manaCostMax: '6',
      keywordKeys: ['flying'],
      tagKeys: ['rare'],
      manaFamilyKeys: ['arcane'],
      manaFamilyExcludeKeys: ['arcane'],
      affinitySymbolKeys: ['sola-affinity'],
      affinitySymbolExcludeKeys: ['sola-affinity'],
      devotionSymbolKeys: ['pray'],
      devotionSymbolExcludeKeys: ['pray'],
      otherSymbolKeys: ['tap'],
      otherSymbolExcludeKeys: ['tap'],
      typeKeys: ['creature'],
      typeExcludeKeys: ['spell'],
    });
  });

  test('builds the mana toggle catalog from card classification definitions', () => {
    const catalog = createCardFilterCatalog(filters);

    expect(catalog.manaFamilies.map((row) => row.key)).toEqual(['arcane']);
    expect(catalog.affinitySymbols.map((row) => row.key)).toEqual(['sola-affinity']);
  });

  test('migrates a paired affinity route key into canonical mana-family selection', () => {
    const selection = buildCardFilterSelectionState(
      {
        ...createEmptyCardFilterState(),
        affinitySymbolKeys: ['arcane-affinity'],
      },
      createCardFilterCatalog(filters),
    );

    expect(selection.manaFamilyIds).toEqual(['arcane']);
    expect(selection.affinitySymbolIds).toEqual([]);
  });

  test('preserves the match mode when migrating an affinity-only predicate', () => {
    const selection = buildCardFilterSelectionState(
      {
        ...createEmptyCardFilterState(),
        affinitySymbolMatch: 'all',
        affinitySymbolKeys: ['arcane-affinity'],
      },
      createCardFilterCatalog(filters),
    );

    expect(selection.manaFamilyMatch).toBe('all');
    expect(selection.manaFamilyIds).toEqual(['arcane']);
  });

  test('keeps mixed legacy affinities in one literal predicate', () => {
    const catalog = createCardFilterCatalog(filters);
    const selection = buildCardFilterSelectionState(
      {
        ...createEmptyCardFilterState(),
        affinitySymbolMatch: 'any',
        affinitySymbolKeys: ['arcane-affinity', 'sola-affinity'],
      },
      catalog,
    );

    expect(selection.manaFamilyIds).toEqual([]);
    expect(selection.affinitySymbolIds).toEqual(['sym-2', 'sym-2b']);
    expect(buildCardFilterStateFromSelection(selection, catalog).affinitySymbolKeys).toEqual([
      'arcane-affinity',
      'sola-affinity',
    ]);
  });

  test('does not infer filter families from raw symbols when classifications are absent', () => {
    const catalog = createCardFilterCatalog({ ...filters, mana_families: undefined });

    expect(catalog.manaFamilies).toEqual([]);
  });

  test('preserves code-owned mana-family route keys without a hydrated catalog', () => {
    const catalog = createCardFilterCatalog({ ...filters, mana_families: undefined });
    const selection = buildCardFilterSelectionState(
      {
        ...createEmptyCardFilterState(),
        manaFamilyMatch: 'all',
        manaFamilyKeys: ['arcane'],
        manaFamilyExcludeKeys: ['dark'],
      },
      catalog,
    );

    expect(selection.manaFamilyMatch).toBe('all');
    expect(selection.manaFamilyIds).toEqual(['arcane']);
    expect(selection.manaFamilyExcludeIds).toEqual(['dark']);
    expect(buildCardFilterStateFromSelection(selection, catalog)).toMatchObject({
      manaFamilyKeys: ['arcane'],
      manaFamilyExcludeKeys: ['dark'],
    });
  });

  test('requires catalog hydration only for legacy mana-family symbol keys', () => {
    expect(cardFilterStateRequiresCatalog({
      ...createEmptyCardFilterState(),
      manaFamilyKeys: ['arcane'],
      manaFamilyExcludeKeys: ['dark'],
    })).toBe(false);
    expect(cardFilterStateRequiresCatalog({
      ...createEmptyCardFilterState(),
      manaFamilyKeys: ['arcane-mana'],
    })).toBe(true);
    expect(cardFilterStateRequiresCatalog({
      ...createEmptyCardFilterState(),
      manaFamilyExcludeKeys: ['dark-affinity'],
    })).toBe(true);
  });

  test('reconciles only unavailable keyword, tag, and type keys', () => {
    const catalog = createCardFilterCatalog(filters);
    const state = {
      ...createEmptyCardFilterState('evil'),
      query: 'dragon',
      keywordMatch: 'all' as const,
      keywordKeys: ['flying', 'missing-keyword'],
      tagMatch: 'all' as const,
      tagKeys: ['missing-tag'],
      typeMatch: 'all' as const,
      typeKeys: ['creature', 'missing-type'],
      typeExcludeKeys: ['spell', 'missing-excluded-type'],
      otherSymbolKeys: ['missing-symbol'],
    };

    const reconciled = reconcileCardFilterStateWithCatalog(state, catalog);

    expect(reconciled).toMatchObject({
      cardPool: 'evil',
      query: 'dragon',
      keywordMatch: 'all',
      keywordKeys: ['flying'],
      tagMatch: 'any',
      tagKeys: [],
      typeMatch: 'all',
      typeKeys: ['creature'],
      typeExcludeKeys: ['spell'],
      otherSymbolKeys: ['missing-symbol'],
    });
    expect(reconcileCardFilterStateWithCatalog(reconciled, catalog)).toEqual(reconciled);
  });

  test('resets type match only after both include and exclude selections disappear', () => {
    const catalog = createCardFilterCatalog(filters);

    const includeRemoved = reconcileCardFilterStateWithCatalog(
      {
        ...createEmptyCardFilterState(),
        typeMatch: 'all',
        typeKeys: ['missing'],
        typeExcludeKeys: ['spell'],
      },
      catalog,
    );
    const allRemoved = reconcileCardFilterStateWithCatalog(
      {
        ...createEmptyCardFilterState(),
        typeMatch: 'all',
        typeKeys: ['missing'],
        typeExcludeKeys: ['also-missing'],
      },
      catalog,
    );

    expect(includeRemoved.typeMatch).toBe('all');
    expect(includeRemoved.typeExcludeKeys).toEqual(['spell']);
    expect(allRemoved.typeMatch).toBe('any');
  });
});

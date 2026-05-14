import { describe, expect, test } from 'vitest';
import {
  createEmptyCardFilterState,
  getCardFilterSignature,
  parseCardFilterRouteQuery,
} from '@/modules/card-filters/cardFilterState';

describe('cardFilterState route adapters', () => {
  test('parses an empty route query into empty filter state', () => {
    expect(parseCardFilterRouteQuery({})).toEqual(createEmptyCardFilterState());
  });

  test('parses repeated route params into the correct filter buckets', () => {
    const state = parseCardFilterRouteQuery({
      q: ' dragons ',
      keyword_keys: ['flying', 'dragon', 'flying'],
      mana_symbol_keys: ['mana-fire', 'mana-water'],
      other_symbol_keys: 'tap',
      type_keys: ['creature'],
    });

    expect(state).toMatchObject({
      query: 'dragons',
      keywordKeys: ['dragon', 'flying'],
      manaSymbolKeys: ['mana-fire', 'mana-water'],
      otherSymbolKeys: ['tap'],
      typeKeys: ['creature'],
    });
  });

  test('produces a stable signature for equivalent filter selections', () => {
    const left = getCardFilterSignature(
      parseCardFilterRouteQuery({
        keyword_keys: ['flying', 'dragon'],
        mana_symbol_keys: ['mana-fire'],
        affinity_symbol_keys: ['air'],
      }),
    );
    const right = getCardFilterSignature(
      parseCardFilterRouteQuery({
        affinity_symbol_keys: ['air'],
        keyword_keys: ['dragon', 'flying'],
        mana_symbol_keys: ['mana-fire'],
      }),
    );

    expect(left).toBe(right);
  });
});

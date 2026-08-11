import { describe, expect, test } from 'vitest';
import { createEmptyCardFilterState } from '@/domain/cards/utils/filters/cardFilterState';
import {
  buildCardFilterRouteQuery,
  getCardFilterSignature,
  parseCardFilterRouteQuery,
} from '@/domain/cards/utils/filters/cardFilterRouteState';

describe('cardFilterRouteState', () => {
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
      type_exclude_keys: ['spell'],
    });

    expect(state).toMatchObject({
      query: 'dragons',
      keywordKeys: ['dragon', 'flying'],
      manaSymbolKeys: ['mana-fire', 'mana-water'],
      otherSymbolKeys: ['tap'],
      typeKeys: ['creature'],
      typeExcludeKeys: ['spell'],
    });

    expect(buildCardFilterRouteQuery(state)).toMatchObject({
      mana_family_keys: ['mana-fire', 'mana-water'],
      type_keys: ['creature'],
      type_exclude_keys: ['spell'],
    });
  });

  test('parses canonical mana-family route params', () => {
    const state = parseCardFilterRouteQuery({
      mana_family_keys: ['arcane', 'dark'],
      mana_family_exclude_keys: ['primal'],
      mana_family_match: 'all',
    });

    expect(state.manaSymbolKeys).toEqual(['arcane', 'dark']);
    expect(state.manaSymbolExcludeKeys).toEqual(['primal']);
    expect(state.manaSymbolMatch).toBe('all');
  });

  test('round-trips non-default lifecycle status through route query state', () => {
    const deprecatedState = parseCardFilterRouteQuery({ lifecycle_status: 'deprecated' });
    const allState = parseCardFilterRouteQuery({ lifecycle_status: 'all' });

    expect(deprecatedState.lifecycleStatus).toBe('deprecated');
    expect(allState.lifecycleStatus).toBe('all');
    expect(buildCardFilterRouteQuery(deprecatedState)).toEqual({ lifecycle_status: 'deprecated' });
    expect(buildCardFilterRouteQuery(allState)).toEqual({ lifecycle_status: 'all' });
    expect(
      buildCardFilterRouteQuery(parseCardFilterRouteQuery({ lifecycle_status: 'active' })),
    ).toEqual({});
  });

  test('round-trips Location through role include and exclude filters', () => {
    const state = parseCardFilterRouteQuery({
      card_roles: ['location', 'event'],
      card_role_exclude: 'boon',
    });

    expect(state.cardRoleKeys).toEqual(['event', 'location']);
    expect(state.cardRoleExcludeKeys).toEqual(['boon']);
    expect(buildCardFilterRouteQuery(state)).toMatchObject({
      card_roles: ['event', 'location'],
      card_role_exclude: ['boon'],
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

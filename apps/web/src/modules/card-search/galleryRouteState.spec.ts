import { describe, expect, test } from 'vitest';
import {
  buildGalleryApiSearchParams,
  createEmptyGalleryFilterState,
  getGalleryFilterSignature,
  parseGalleryFilterState,
} from './galleryRouteState';

describe('galleryRouteState', () => {
  test('parses an empty route query into empty filter state', () => {
    expect(parseGalleryFilterState({})).toEqual(createEmptyGalleryFilterState());
  });

  test('parses repeated route params into the correct filter buckets', () => {
    const state = parseGalleryFilterState({
      q: ' dragons ',
      keyword_ids: ['k-2', 'k-1', 'k-2'],
      mana_type_symbol_ids: ['m-2', 'm-1'],
      other_symbol_ids: 'o-1',
      type_ids: ['t-1'],
    });

    expect(state).toMatchObject({
      query: 'dragons',
      keywordIds: ['k-1', 'k-2'],
      manaTypeSymbolIds: ['m-1', 'm-2'],
      otherSymbolIds: ['o-1'],
      typeIds: ['t-1'],
    });
  });

  test('produces a stable signature for equivalent filter selections', () => {
    const left = getGalleryFilterSignature(
      parseGalleryFilterState({
        keyword_ids: ['k-2', 'k-1'],
        mana_type_symbol_ids: ['m-1'],
        affinity_symbol_ids: ['a-1'],
      }),
    );
    const right = getGalleryFilterSignature(
      parseGalleryFilterState({
        affinity_symbol_ids: ['a-1'],
        keyword_ids: ['k-1', 'k-2'],
        mana_type_symbol_ids: ['m-1'],
      }),
    );

    expect(left).toBe(right);
  });

  test('merges symbol filter buckets into API symbol_ids params', () => {
    const params = buildGalleryApiSearchParams(
      parseGalleryFilterState({
        mana_type_symbol_ids: ['m-1'],
        affinity_symbol_ids: ['a-1'],
        devotion_symbol_ids: ['d-1'],
        other_symbol_ids: ['o-1'],
      }),
    );

    expect(params.getAll('symbol_ids')).toEqual(['a-1', 'd-1', 'm-1', 'o-1']);
    expect(params.getAll('mana_type_symbol_ids')).toEqual([]);
  });
});


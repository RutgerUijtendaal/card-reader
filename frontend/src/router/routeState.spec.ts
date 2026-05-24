import { describe, expect, test } from 'vitest';
import {
  addReturnToQuery,
  clearLocationQueryKeys,
  mergeLocationQuery,
  queryString,
} from '@/router/routeState';

describe('routeState', () => {
  test('normalizes query string values', () => {
    expect(queryString('deck-1')).toBe('deck-1');
    expect(queryString('')).toBeNull();
    expect(queryString(['deck-1'])).toBeNull();
  });

  test('merges updates without dropping unrelated keys', () => {
    expect(
      mergeLocationQuery(
        {
          foo: 'bar',
          deck_id: 'deck-1',
        },
        {
          deck_id: null,
          admin_tab: 'catalog',
        },
      ),
    ).toEqual({
      foo: 'bar',
      admin_tab: 'catalog',
    });
  });

  test('adds return context and clears transient keys', () => {
    const withReturn = addReturnToQuery(
      { foo: 'bar' },
      'deck',
      { deck_id: 'deck-1' },
    );

    expect(withReturn).toEqual({
      foo: 'bar',
      deck_id: 'deck-1',
      return_to: 'deck',
    });

    expect(clearLocationQueryKeys(withReturn as never, ['deck_id', 'return_to'])).toEqual({
      foo: 'bar',
    });
  });
});

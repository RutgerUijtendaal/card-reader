import { describe, expect, test } from 'vitest';
import {
  buildDeckCardDetailLocation,
  buildDeckReturnLocation,
  isDeckReturnQuery,
} from '@/modules/decks/deckRouteState';

describe('deckRouteState', () => {
  test('builds card detail location that preserves deck return context', () => {
    expect(
      buildDeckCardDetailLocation('card-1', 'deck-1', {
        foo: 'bar',
      }),
    ).toEqual({
      path: '/cards/card-1',
      query: {
        foo: 'bar',
        deck_id: 'deck-1',
        return_to: 'deck',
      },
    });
  });

  test('builds deck return location by dropping deck return keys only', () => {
    const query = {
      foo: 'bar',
      deck_id: 'deck-1',
      return_to: 'deck',
    };

    expect(isDeckReturnQuery(query)).toBe(true);
    expect(buildDeckReturnLocation(query)).toEqual({
      path: '/decks/deck-1',
      query: {
        foo: 'bar',
      },
    });
  });
});

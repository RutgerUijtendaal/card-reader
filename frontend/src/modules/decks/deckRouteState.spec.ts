import { describe, expect, test } from 'vitest';
import {
  buildDeckCardDetailLocation,
  buildDeckDetailEditorLocation,
  buildDeckEditorReturnLocation,
  buildDeckReturnLocation,
  buildMyDeckEditorLocation,
  buildMyDecksLocation,
  buildMyDecksReturnLocation,
  buildNewDeckEditorLocation,
  getMyDecksReturnLabel,
  getDeckEditorReturnLabel,
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

  test('builds a my decks editor location with return context', () => {
    expect(buildMyDeckEditorLocation('deck-1')).toEqual({
      path: '/my/decks/deck-1/edit',
      query: {
        return_to: 'my_decks',
      },
    });
  });

  test('builds a my decks location with public decks return context', () => {
    expect(buildMyDecksLocation('decks')).toEqual({
      path: '/my/decks',
      query: {
        return_to: 'decks',
      },
    });
  });

  test('builds a new deck editor location with public decks return context', () => {
    expect(buildNewDeckEditorLocation('decks')).toEqual({
      path: '/my/decks/new',
      query: {
        return_to: 'decks',
      },
    });
  });

  test('builds a deck detail editor location with return context', () => {
    expect(buildDeckDetailEditorLocation('deck-1')).toEqual({
      path: '/my/decks/deck-1/edit',
      query: {
        return_to: 'deck',
        deck_id: 'deck-1',
      },
    });
  });

  test('returns deck detail from the editor when deck context is present', () => {
    const query = {
      foo: 'bar',
      return_to: 'deck',
      deck_id: 'deck-1',
    };

    expect(getDeckEditorReturnLabel(query)).toBe('Deck');
    expect(buildDeckEditorReturnLocation(query)).toEqual({
      path: '/my/decks/deck-1',
      query: {
        foo: 'bar',
      },
    });
  });

  test('falls back to my decks from the editor without deck detail context', () => {
    const query = {
      foo: 'bar',
      return_to: 'my_decks',
    };

    expect(getDeckEditorReturnLabel(query)).toBe('My Decks');
    expect(buildDeckEditorReturnLocation(query)).toEqual({
      path: '/my/decks',
      query: {
        foo: 'bar',
      },
    });
  });

  test('returns public decks from the editor when public browse context is present', () => {
    const query = {
      foo: 'bar',
      return_to: 'decks',
    };

    expect(getDeckEditorReturnLabel(query)).toBe('Decks');
    expect(buildDeckEditorReturnLocation(query)).toEqual({
      path: '/decks',
      query: {
        foo: 'bar',
      },
    });
  });

  test('returns public decks from my decks when public browse context is present', () => {
    const query = {
      foo: 'bar',
      return_to: 'decks',
    };

    expect(getMyDecksReturnLabel(query)).toBe('Decks');
    expect(buildMyDecksReturnLocation(query)).toEqual({
      path: '/decks',
      query: {
        foo: 'bar',
      },
    });
  });
});

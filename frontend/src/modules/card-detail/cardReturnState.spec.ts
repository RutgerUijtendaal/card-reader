import { describe, expect, test } from 'vitest';
import { buildCardReturnLocation, getCardReturnLabel } from '@/modules/card-detail/cardReturnState';

describe('cardReturnState', () => {
  test('uses admin return context when present', () => {
    const query = {
      admin_tab: 'catalog',
      return_to: 'admin',
    };

    expect(getCardReturnLabel(query)).toBe('Admin');
    expect(buildCardReturnLocation(query)).toEqual({
      path: '/admin',
      query: {
        admin_tab: 'catalog',
      },
    });
  });

  test('uses deck return context when present', () => {
    const query = {
      deck_id: 'deck-1',
      return_to: 'deck',
    };

    expect(getCardReturnLabel(query)).toBe('Deck');
    expect(buildCardReturnLocation(query)).toEqual({
      path: '/decks/deck-1',
      query: {},
    });
  });

  test('falls back to the gallery when no explicit return context exists', () => {
    expect(getCardReturnLabel({ q: 'dragon' })).toBe('Gallery');
    expect(buildCardReturnLocation({ q: 'dragon' })).toEqual({
      path: '/cards',
      query: {
        q: 'dragon',
      },
    });
  });
});

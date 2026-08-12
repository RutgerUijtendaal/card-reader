import { describe, expect, test } from 'vitest';
import {
  CARD_POOL_OPTIONS,
  cardPoolLabel,
  isCardPool,
  normalizeCardPool,
} from './cardPools';

describe('cardPools', () => {
  test('owns the canonical ordered pool registry and labels', () => {
    expect(CARD_POOL_OPTIONS).toEqual([
      { value: 'player', label: 'Player', rank: 0 },
      { value: 'evil', label: 'Evil', rank: 1 },
      { value: 'neutral', label: 'Neutral', rank: 2 },
    ]);
    expect(cardPoolLabel('neutral')).toBe('Neutral');
  });

  test('normalizes invalid and obsolete route values to Player', () => {
    expect(isCardPool('evil')).toBe(true);
    expect(normalizeCardPool('neutral')).toBe('neutral');
    expect(normalizeCardPool('game_master')).toBe('player');
    expect(normalizeCardPool('unknown')).toBe('player');
  });
});

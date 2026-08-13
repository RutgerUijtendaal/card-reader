import { describe, expect, test } from 'vitest';
import {
  CARD_FACTION_OPTIONS,
  displayCardFactionLabels,
  isCardFaction,
} from '@/domain/cards/cardFactions';

describe('card faction registry', () => {
  test('owns canonical faction ordering, validation, and display labels', () => {
    expect(CARD_FACTION_OPTIONS).toEqual([
      { value: 'order', label: 'Order' },
      { value: 'blood', label: 'Blood' },
      { value: 'darkness', label: 'Darkness' },
    ]);
    expect(isCardFaction('blood')).toBe(true);
    expect(isCardFaction('unknown')).toBe(false);
    expect(displayCardFactionLabels(['order', 'darkness'])).toEqual([
      'Order',
      'Darkness',
    ]);
    expect(displayCardFactionLabels([])).toEqual(['No faction']);
  });
});

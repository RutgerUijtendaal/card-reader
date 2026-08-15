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
      { value: 'dark', label: 'Dark' },
      { value: 'metal', label: 'Metal' },
    ]);
    expect(isCardFaction('blood')).toBe(true);
    expect(isCardFaction('dark')).toBe(true);
    expect(isCardFaction('metal')).toBe(true);
    expect(isCardFaction('darkness')).toBe(false);
    expect(isCardFaction('unknown')).toBe(false);
    expect(displayCardFactionLabels(['order', 'dark', 'metal'])).toEqual(['Order', 'Dark', 'Metal']);
    expect(displayCardFactionLabels([])).toEqual(['No faction']);
  });
});

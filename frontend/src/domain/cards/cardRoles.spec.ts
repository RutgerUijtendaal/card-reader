import { describe, expect, test } from 'vitest';
import {
  CARD_ROLE_FILTER_VALUES,
  CARD_ROLE_OPTIONS,
  displayCardRoleLabels,
  isCardRoleFilter,
} from '@/domain/cards/cardRoles';

describe('card role registry', () => {
  test('owns canonical role ordering, filtering, and display labels', () => {
    expect(CARD_ROLE_OPTIONS).toEqual([
      { value: 'hero', label: 'Hero' },
      { value: 'boon', label: 'Boon' },
      { value: 'event', label: 'Event' },
      { value: 'location', label: 'Location' },
    ]);
    expect(CARD_ROLE_FILTER_VALUES).toEqual([
      'standard',
      'hero',
      'boon',
      'event',
      'location',
    ]);
    expect(isCardRoleFilter('location')).toBe(true);
    expect(isCardRoleFilter('unknown')).toBe(false);
    expect(displayCardRoleLabels(['event', 'location'])).toEqual(['Event', 'Location']);
    expect(displayCardRoleLabels([])).toEqual(['Standard']);
  });
});

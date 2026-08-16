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
      { value: 'boss', label: 'Boss' },
      { value: 'location', label: 'Location' },
      { value: 'boon', label: 'Boon' },
      { value: 'event', label: 'Event' },
      { value: 'shop_item', label: 'Shop Item' },
      { value: 'directive', label: 'Directive' },
      { value: 'reminder', label: 'Reminder' },
      { value: 'mana', label: 'Mana' },
    ]);
    expect(CARD_ROLE_FILTER_VALUES).toEqual([
      'standard',
      'hero',
      'boss',
      'location',
      'boon',
      'event',
      'shop_item',
      'directive',
      'reminder',
      'mana',
    ]);
    expect(isCardRoleFilter('location')).toBe(true);
    expect(isCardRoleFilter('directive')).toBe(true);
    expect(isCardRoleFilter('reminder')).toBe(true);
    expect(isCardRoleFilter('unknown')).toBe(false);
    expect(displayCardRoleLabels(['reminder', 'event', 'location', 'directive', 'mana'])).toEqual([
      'Reminder',
      'Event',
      'Location',
      'Directive',
      'Mana',
    ]);
    expect(displayCardRoleLabels([])).toEqual(['Normal']);
  });
});

import { beforeEach, describe, expect, test } from 'vitest';
import {
  MANA_TYPE_GROUPS_STORAGE_KEY,
  normalizeManaTypeGroupsStorage,
  useManaTypeGroups,
  validateManaTypeGroups,
} from '@/composables/decks/useManaTypeGroups';

describe('mana type group preferences', () => {
  beforeEach(() => {
    localStorage.clear();
    useManaTypeGroups().saveGroups([]);
  });

  test('normalizes malformed, duplicate, and invalid stored groups', () => {
    expect(normalizeManaTypeGroupsStorage(null).groups).toEqual([]);
    expect(normalizeManaTypeGroupsStorage({ version: 2, groups: [] }).groups).toEqual([]);
    expect(normalizeManaTypeGroupsStorage({
      version: 1,
      groups: [
        { id: 'one', name: 'Spells', typeKeys: [' Spell ', 'spell'] },
        { id: 'two', name: 'spells', typeKeys: ['attachment'] },
        { id: 'three', name: '', typeKeys: ['follower'] },
        { id: 'four', name: 'Empty', typeKeys: [] },
      ],
    }).groups).toEqual([{ id: 'one', name: 'Spells', typeKeys: ['spell'] }]);
  });

  test('reports empty names, duplicate names, and missing available types', () => {
    const errors = validateManaTypeGroups([
      { id: 'one', name: '', typeKeys: ['spell'] },
      { id: 'two', name: 'Units', typeKeys: ['removed-type'] },
      { id: 'three', name: 'units', typeKeys: ['follower'] },
    ], new Set(['spell', 'follower']));

    expect(errors).toEqual([
      { groupId: 'one', message: 'Enter a group name.' },
      { groupId: 'two', message: 'Select at least one card type.' },
      { groupId: 'three', message: 'Group names must be unique.' },
    ]);
  });

  test('persists ordered groups and shares live state between instances', () => {
    const first = useManaTypeGroups();
    const second = useManaTypeGroups();
    first.saveGroups([
      { id: 'attachments', name: 'Attachments', typeKeys: ['attachment'] },
      { id: 'spells', name: 'Spells', typeKeys: ['spell'] },
    ]);

    expect(second.groups.value.map((group) => group.id)).toEqual(['attachments', 'spells']);
    expect(JSON.parse(localStorage.getItem(MANA_TYPE_GROUPS_STORAGE_KEY) ?? '{}')).toEqual({
      version: 1,
      groups: [
        { id: 'attachments', name: 'Attachments', typeKeys: ['attachment'] },
        { id: 'spells', name: 'Spells', typeKeys: ['spell'] },
      ],
    });

    second.saveGroups([{ id: 'spells', name: 'Updated Spells', typeKeys: ['spell'] }]);
    expect(first.groups.value).toEqual([{ id: 'spells', name: 'Updated Spells', typeKeys: ['spell'] }]);
  });
});

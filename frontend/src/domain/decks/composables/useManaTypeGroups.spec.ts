import { beforeEach, describe, expect, test } from 'vitest';
import {
  MANA_TYPE_GROUPS_STORAGE_KEY,
  normalizeManaTypeGroupsStorage,
  useManaTypeGroups,
  validateManaTypeGroups,
} from '@/domain/decks/composables/useManaTypeGroups';

describe('mana type group preferences', () => {
  beforeEach(() => {
    localStorage.clear();
    useManaTypeGroups().saveGroups([]);
  });

  test('normalizes malformed, duplicate, and invalid stored groups', () => {
    expect(normalizeManaTypeGroupsStorage(null).groups).toEqual([]);
    expect(normalizeManaTypeGroupsStorage({ version: 4, groups: [] }).groups).toEqual([]);
    expect(normalizeManaTypeGroupsStorage({
      version: 1,
      groups: [
        {
          id: 'one',
          name: 'Spells',
          typeKeys: [' Spell ', 'spell', 'attachment'],
          excludedTypeKeys: [' Follower ', 'spell'],
        },
        { id: 'two', name: 'spells', typeKeys: ['attachment', 'follower'] },
        { id: 'three', name: '', typeKeys: ['follower', 'spell'] },
        { id: 'four', name: 'Empty', typeKeys: [] },
        {
          id: 'five',
          name: 'Mixed rules',
          typeKeys: ['spell'],
          excludedTypeKeys: ['follower'],
        },
      ],
    }).groups).toEqual([
      {
        id: 'one',
        name: 'Spells',
        typeKeys: ['spell', 'attachment'],
        excludedTypeKeys: ['follower'],
        isVisible: true,
      },
      {
        id: 'five',
        name: 'Mixed rules',
        typeKeys: ['spell'],
        excludedTypeKeys: ['follower'],
        isVisible: true,
      },
    ]);
  });

  test('reports empty names, duplicate names, and missing available types', () => {
    const errors = validateManaTypeGroups([
      {
        id: 'one',
        name: '',
        typeKeys: ['spell', 'follower'],
        excludedTypeKeys: [],
        isVisible: true,
      },
      {
        id: 'two',
        name: 'Units',
        typeKeys: ['removed-type', 'spell'],
        excludedTypeKeys: [],
        isVisible: true,
      },
      {
        id: 'three',
        name: 'units',
        typeKeys: ['follower', 'spell'],
        excludedTypeKeys: [],
        isVisible: true,
      },
      {
        id: 'four',
        name: 'Actions',
        typeKeys: ['spell', 'follower'],
        excludedTypeKeys: ['spell'],
        isVisible: true,
      },
    ], new Set(['spell', 'follower']));

    expect(errors).toEqual([
      { groupId: 'one', message: 'Enter a group name.' },
      { groupId: 'two', message: 'Activate at least two card types.' },
      { groupId: 'three', message: 'Group names must be unique.' },
      { groupId: 'four', message: 'A type cannot be both included and excluded.' },
    ]);
  });

  test('persists ordered groups and shares live state between instances', () => {
    const first = useManaTypeGroups();
    const second = useManaTypeGroups();
    first.saveGroups([
      {
        id: 'attachments',
        name: 'Attachments',
        typeKeys: ['attachment', 'follower'],
        excludedTypeKeys: [],
        isVisible: true,
      },
      {
        id: 'spells',
        name: 'Spells',
        typeKeys: ['spell', 'attachment'],
        excludedTypeKeys: ['follower'],
        isVisible: false,
      },
    ]);

    expect(second.groups.value.map((group) => group.id)).toEqual(['attachments', 'spells']);
    expect(JSON.parse(localStorage.getItem(MANA_TYPE_GROUPS_STORAGE_KEY) ?? '{}')).toEqual({
      version: 3,
      groups: [
        {
          id: 'attachments',
          name: 'Attachments',
          typeKeys: ['attachment', 'follower'],
          excludedTypeKeys: [],
          isVisible: true,
        },
        {
          id: 'spells',
          name: 'Spells',
          typeKeys: ['spell', 'attachment'],
          excludedTypeKeys: ['follower'],
          isVisible: false,
        },
      ],
    });

    second.saveGroups([{
      id: 'spells',
      name: 'Updated Spells',
      typeKeys: ['spell', 'attachment'],
      excludedTypeKeys: ['follower'],
      isVisible: false,
    }]);
    expect(first.groups.value).toEqual([{
      id: 'spells',
      name: 'Updated Spells',
      typeKeys: ['spell', 'attachment'],
      excludedTypeKeys: ['follower'],
      isVisible: false,
    }]);
  });
});

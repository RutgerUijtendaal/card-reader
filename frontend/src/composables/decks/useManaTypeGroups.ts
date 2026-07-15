import { computed } from 'vue';
import { createGlobalState, useLocalStorage } from '@vueuse/core';
import type { ManaTypeGroup } from '@/composables/decks/manaDistribution';

export const MANA_TYPE_GROUPS_STORAGE_KEY = 'card-reader.deck-mana-groups';
export const MANA_TYPE_GROUPS_STORAGE_VERSION = 1;

export type ManaTypeGroupsStorage = {
  version: typeof MANA_TYPE_GROUPS_STORAGE_VERSION;
  groups: ManaTypeGroup[];
};

export type ManaTypeGroupValidationError = {
  groupId: string;
  message: string;
};

const EMPTY_STORAGE: ManaTypeGroupsStorage = {
  version: MANA_TYPE_GROUPS_STORAGE_VERSION,
  groups: [],
};

const normalizeStringList = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return [...new Set(
    value
      .filter((entry): entry is string => typeof entry === 'string')
      .map((entry) => entry.trim().toLowerCase())
      .filter(Boolean),
  )];
};

const normalizeGroup = (value: unknown): ManaTypeGroup | null => {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const group = value as Partial<Record<keyof ManaTypeGroup, unknown>>;
  const id = typeof group.id === 'string' ? group.id.trim() : '';
  const name = typeof group.name === 'string' ? group.name.trim() : '';
  const typeKeys = normalizeStringList(group.typeKeys);
  if (!id || !name || typeKeys.length === 0) {
    return null;
  }
  return { id, name, typeKeys };
};

export const normalizeManaTypeGroupsStorage = (value: unknown): ManaTypeGroupsStorage => {
  if (!value || typeof value !== 'object') {
    return { ...EMPTY_STORAGE, groups: [] };
  }
  const storage = value as { version?: unknown; groups?: unknown };
  if (storage.version !== MANA_TYPE_GROUPS_STORAGE_VERSION || !Array.isArray(storage.groups)) {
    return { ...EMPTY_STORAGE, groups: [] };
  }

  const ids = new Set<string>();
  const names = new Set<string>();
  const groups: ManaTypeGroup[] = [];
  for (const rawGroup of storage.groups) {
    const group = normalizeGroup(rawGroup);
    const normalizedName = group?.name.toLowerCase() ?? '';
    if (!group || ids.has(group.id) || names.has(normalizedName)) {
      continue;
    }
    ids.add(group.id);
    names.add(normalizedName);
    groups.push(group);
  }
  return { version: MANA_TYPE_GROUPS_STORAGE_VERSION, groups };
};

export const validateManaTypeGroups = (
  groups: ManaTypeGroup[],
  availableTypeKeys?: ReadonlySet<string>,
): ManaTypeGroupValidationError[] => {
  const errors: ManaTypeGroupValidationError[] = [];
  const names = new Set<string>();

  for (const group of groups) {
    const name = group.name.trim();
    const normalizedName = name.toLowerCase();
    const normalizedTypeKeys = normalizeStringList(group.typeKeys);
    if (!name) {
      errors.push({ groupId: group.id, message: 'Enter a group name.' });
    } else if (names.has(normalizedName)) {
      errors.push({ groupId: group.id, message: 'Group names must be unique.' });
    }
    names.add(normalizedName);

    const validTypeKeys = availableTypeKeys
      ? normalizedTypeKeys.filter((key) => availableTypeKeys.has(key))
      : normalizedTypeKeys;
    if (validTypeKeys.length === 0) {
      errors.push({ groupId: group.id, message: 'Select at least one card type.' });
    }
  }
  return errors;
};

const useManaTypeGroupsState = createGlobalState(() => {
  const stored = useLocalStorage<ManaTypeGroupsStorage>(MANA_TYPE_GROUPS_STORAGE_KEY, EMPTY_STORAGE, {
    flush: 'sync',
    serializer: {
      read: (value) => {
        try {
          return normalizeManaTypeGroupsStorage(JSON.parse(value));
        } catch {
          return { ...EMPTY_STORAGE, groups: [] };
        }
      },
      write: (value) => JSON.stringify(normalizeManaTypeGroupsStorage(value)),
    },
  });

  const groups = computed(() => normalizeManaTypeGroupsStorage(stored.value).groups);

  const saveGroups = (nextGroups: ManaTypeGroup[]): void => {
    stored.value = normalizeManaTypeGroupsStorage({
      version: MANA_TYPE_GROUPS_STORAGE_VERSION,
      groups: nextGroups,
    });
  };

  return { groups, saveGroups };
});

export const useManaTypeGroups = () => useManaTypeGroupsState();

export const createManaTypeGroupId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `mana-group-${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

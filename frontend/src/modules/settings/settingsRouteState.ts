import type { LocationQuery, LocationQueryRaw, RouteLocationRaw } from 'vue-router';
import type { CatalogKind } from '@/modules/settings/types';

export type SettingsTab = 'catalog' | 'templates' | 'card-groups' | 'users' | 'maintenance';

const SETTINGS_RETURN_TO = 'settings';
const SETTINGS_TAB_QUERY_KEY = 'settings_tab';
const SETTINGS_KIND_QUERY_KEY = 'settings_kind';
const SETTINGS_ENTRY_QUERY_KEY = 'settings_entry';
const SETTINGS_RETURN_TO_QUERY_KEY = 'return_to';

const CATALOG_KINDS: CatalogKind[] = [
  'keywords',
  'tags',
  'symbols',
  'types',
  'suggested-tags',
  'suggested-types',
];

const SETTINGS_TABS: SettingsTab[] = ['catalog', 'templates', 'card-groups', 'users', 'maintenance'];

const queryString = (value: unknown): string | null =>
  typeof value === 'string' && value.trim().length > 0 ? value : null;

export const parseSettingsTab = (
  query: LocationQuery,
  options: { allowUsers: boolean; allowMaintenance: boolean },
): SettingsTab => {
  const value = queryString(query[SETTINGS_TAB_QUERY_KEY]);
  if (!value || !SETTINGS_TABS.includes(value as SettingsTab)) {
    return 'catalog';
  }
  if (value === 'users' && !options.allowUsers) {
    return 'catalog';
  }
  if (value === 'maintenance' && !options.allowMaintenance) {
    return 'catalog';
  }
  return value as SettingsTab;
};

export const parseSettingsCatalogKind = (query: LocationQuery): CatalogKind => {
  const value = queryString(query[SETTINGS_KIND_QUERY_KEY]);
  if (!value || !CATALOG_KINDS.includes(value as CatalogKind)) {
    return 'keywords';
  }
  return value as CatalogKind;
};

export const parseSettingsEntryId = (query: LocationQuery): string | null =>
  queryString(query[SETTINGS_ENTRY_QUERY_KEY]);

export const buildSettingsQuery = (
  query: LocationQuery,
  updates: {
    tab?: SettingsTab | null;
    kind?: CatalogKind | null;
    entryId?: string | null;
  },
): LocationQueryRaw => {
  const nextQuery: LocationQueryRaw = { ...query };

  if (updates.tab !== undefined) {
    if (updates.tab) {
      nextQuery[SETTINGS_TAB_QUERY_KEY] = updates.tab;
    } else {
      delete nextQuery[SETTINGS_TAB_QUERY_KEY];
    }
  }

  if (updates.kind !== undefined) {
    if (updates.kind) {
      nextQuery[SETTINGS_KIND_QUERY_KEY] = updates.kind;
    } else {
      delete nextQuery[SETTINGS_KIND_QUERY_KEY];
    }
  }

  if (updates.entryId !== undefined) {
    if (updates.entryId) {
      nextQuery[SETTINGS_ENTRY_QUERY_KEY] = updates.entryId;
    } else {
      delete nextQuery[SETTINGS_ENTRY_QUERY_KEY];
    }
  }

  return nextQuery;
};

export const buildSettingsCardDetailLocation = (
  cardId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: `/cards/${cardId}/edit`,
  query: {
    ...query,
    [SETTINGS_RETURN_TO_QUERY_KEY]: SETTINGS_RETURN_TO,
  },
});

export const isSettingsReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[SETTINGS_RETURN_TO_QUERY_KEY]) === SETTINGS_RETURN_TO;

export const buildSettingsReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  const nextQuery: LocationQueryRaw = { ...query };
  delete nextQuery[SETTINGS_RETURN_TO_QUERY_KEY];
  return {
    path: '/settings',
    query: nextQuery,
  };
};

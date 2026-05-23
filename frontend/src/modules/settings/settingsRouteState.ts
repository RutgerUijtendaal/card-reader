import type { LocationQuery, LocationQueryRaw, RouteLocationRaw } from 'vue-router';
import type { CatalogKind } from '@/modules/settings/types';
import { addReturnToQuery, clearLocationQueryKeys, mergeLocationQuery, queryString } from '@/router/routeState';

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
  const nextUpdates: Record<string, string | null | undefined> = {};

  if (updates.tab !== undefined) {
    nextUpdates[SETTINGS_TAB_QUERY_KEY] = updates.tab;
  }
  if (updates.kind !== undefined) {
    nextUpdates[SETTINGS_KIND_QUERY_KEY] = updates.kind;
  }
  if (updates.entryId !== undefined) {
    nextUpdates[SETTINGS_ENTRY_QUERY_KEY] = updates.entryId;
  }

  return mergeLocationQuery(query, nextUpdates);
};

export const buildSettingsCardDetailLocation = (
  cardId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: `/cards/${cardId}/edit`,
  query: addReturnToQuery(query, SETTINGS_RETURN_TO),
});

export const isSettingsReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[SETTINGS_RETURN_TO_QUERY_KEY]) === SETTINGS_RETURN_TO;

export const buildSettingsReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  return {
    path: '/settings',
    query: clearLocationQueryKeys(query, [SETTINGS_RETURN_TO_QUERY_KEY]),
  };
};

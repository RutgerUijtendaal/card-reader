import type { LocationQuery, LocationQueryRaw, RouteLocationRaw } from 'vue-router';
import type { CatalogKind } from '@/modules/admin/types';
import { addReturnToQuery, clearLocationQueryKeys, mergeLocationQuery, queryString } from '@/router/routeState';

export type AdminTab =
  | 'catalog'
  | 'versions'
  | 'templates'
  | 'card-backs'
  | 'card-groups'
  | 'card-merges'
  | 'users'
  | 'maintenance';

const ADMIN_RETURN_TO = 'admin';
const ADMIN_TAB_QUERY_KEY = 'admin_tab';
const ADMIN_KIND_QUERY_KEY = 'admin_kind';
const ADMIN_ENTRY_QUERY_KEY = 'admin_entry';
const ADMIN_MERGE_TARGET_QUERY_KEY = 'admin_merge_target';
const ADMIN_MERGE_SOURCE_QUERY_KEY = 'admin_merge_source';
const ADMIN_RETURN_TO_QUERY_KEY = 'return_to';

const CATALOG_KINDS: CatalogKind[] = [
  'keywords',
  'tags',
  'symbols',
  'types',
  'suggested-tags',
  'suggested-types',
];

const ADMIN_TABS: AdminTab[] = [
  'catalog',
  'versions',
  'templates',
  'card-backs',
  'card-groups',
  'card-merges',
  'users',
  'maintenance',
];

export const parseAdminTab = (
  query: LocationQuery,
  options: { allowUsers: boolean; allowMaintenance: boolean },
): AdminTab => {
  const value = queryString(query[ADMIN_TAB_QUERY_KEY]);
  if (!value || !ADMIN_TABS.includes(value as AdminTab)) {
    return 'catalog';
  }
  if (value === 'users' && !options.allowUsers) {
    return 'catalog';
  }
  if (value === 'maintenance' && !options.allowMaintenance) {
    return 'catalog';
  }
  return value as AdminTab;
};

export const parseAdminCatalogKind = (query: LocationQuery): CatalogKind => {
  const value = queryString(query[ADMIN_KIND_QUERY_KEY]);
  if (!value || !CATALOG_KINDS.includes(value as CatalogKind)) {
    return 'keywords';
  }
  return value as CatalogKind;
};

export const parseAdminEntryId = (query: LocationQuery): string | null =>
  queryString(query[ADMIN_ENTRY_QUERY_KEY]);

export const buildAdminQuery = (
  query: LocationQuery,
  updates: {
    tab?: AdminTab | null;
    kind?: CatalogKind | null;
    entryId?: string | null;
    mergeTargetId?: string | null;
    mergeSourceId?: string | null;
  },
): LocationQueryRaw => {
  const nextUpdates: Record<string, string | null | undefined> = {};

  if (updates.tab !== undefined) {
    nextUpdates[ADMIN_TAB_QUERY_KEY] = updates.tab;
  }
  if (updates.kind !== undefined) {
    nextUpdates[ADMIN_KIND_QUERY_KEY] = updates.kind;
  }
  if (updates.entryId !== undefined) {
    nextUpdates[ADMIN_ENTRY_QUERY_KEY] = updates.entryId;
  }
  if (updates.mergeTargetId !== undefined) {
    nextUpdates[ADMIN_MERGE_TARGET_QUERY_KEY] = updates.mergeTargetId;
  }
  if (updates.mergeSourceId !== undefined) {
    nextUpdates[ADMIN_MERGE_SOURCE_QUERY_KEY] = updates.mergeSourceId;
  }

  return mergeLocationQuery(query, nextUpdates);
};

export const buildAdminCardDetailLocation = (
  cardId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: `/cards/${cardId}/edit`,
  query: addReturnToQuery(query, ADMIN_RETURN_TO),
});

export const parseAdminMergeTargetId = (query: LocationQuery): string | null =>
  queryString(query[ADMIN_MERGE_TARGET_QUERY_KEY]);

export const parseAdminMergeSourceId = (query: LocationQuery): string | null =>
  queryString(query[ADMIN_MERGE_SOURCE_QUERY_KEY]);

export const buildAdminCardMergeLocation = (
  cardId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: '/admin',
  query: buildAdminQuery(query, { tab: 'card-merges', mergeTargetId: cardId }),
});

export const buildAdminCardMergeSourceLocation = (
  cardId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: '/admin',
  query: buildAdminQuery(query, { tab: 'card-merges', mergeSourceId: cardId }),
});

export const isAdminReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[ADMIN_RETURN_TO_QUERY_KEY]) === ADMIN_RETURN_TO;

export const buildAdminReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  return {
    path: '/admin',
    query: clearLocationQueryKeys(query, [ADMIN_RETURN_TO_QUERY_KEY]),
  };
};

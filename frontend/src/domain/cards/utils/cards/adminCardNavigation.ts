import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { clearLocationQueryKeys, mergeLocationQuery, queryString } from '@/shared/router/routeState';

const ADMIN_RETURN_TO = 'admin';
const ADMIN_RETURN_TO_QUERY_KEY = 'return_to';

export const buildAdminCardMergeSourceLocation = (
  cardId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: '/admin',
  query: mergeLocationQuery(query, {
    admin_tab: 'card-merges',
    admin_merge_source: cardId,
  }),
});

export const isAdminReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[ADMIN_RETURN_TO_QUERY_KEY]) === ADMIN_RETURN_TO;

export const buildAdminReturnLocation = (query: LocationQuery): RouteLocationRaw => ({
  path: '/admin',
  query: clearLocationQueryKeys(query, [ADMIN_RETURN_TO_QUERY_KEY]),
});

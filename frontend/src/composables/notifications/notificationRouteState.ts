import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { addReturnToQuery, queryString } from '@/router/routeState';

const NOTIFICATIONS_RETURN_TO = 'notifications';
const RETURN_TO_QUERY_KEY = 'return_to';

export const isNotificationsReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[RETURN_TO_QUERY_KEY]) === NOTIFICATIONS_RETURN_TO;

export const buildNotificationTargetLocation = (
  path: string,
  query: LocationQuery = {},
): RouteLocationRaw => ({
  path,
  query: addReturnToQuery(query, NOTIFICATIONS_RETURN_TO),
});

export const buildNotificationsReturnLocation = (): RouteLocationRaw => ({
  path: '/notifications',
});

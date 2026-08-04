import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { mergeLocationQuery, queryString } from '@/shared/router/routeState';

export type SettingsTab = 'display' | 'sort' | 'hover' | 'developer-data';

const SETTINGS_TAB_QUERY_KEY = 'settings_tab';
const SETTINGS_TABS: SettingsTab[] = ['display', 'sort', 'hover', 'developer-data'];

export const parseSettingsTab = (
  query: LocationQuery,
  options: { allowDeveloperData: boolean },
): SettingsTab => {
  const value = queryString(query[SETTINGS_TAB_QUERY_KEY]);
  if (!value || !SETTINGS_TABS.includes(value as SettingsTab)) {
    return 'display';
  }
  if (value === 'developer-data' && !options.allowDeveloperData) {
    return 'display';
  }
  return value as SettingsTab;
};

export const buildSettingsTabLocation = (
  tab: SettingsTab,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: '/settings',
  query: mergeLocationQuery(query, { [SETTINGS_TAB_QUERY_KEY]: tab }),
});

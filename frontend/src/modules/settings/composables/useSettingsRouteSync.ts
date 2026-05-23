import { useRoute, useRouter } from 'vue-router';
import { buildSettingsQuery, type SettingsTab } from '@/modules/settings/settingsRouteState';
import type { CatalogKind } from '@/modules/settings/types';

type SettingsRouteUpdates = {
  tab?: SettingsTab | null;
  kind?: CatalogKind | null;
  entryId?: string | null;
};

export const useSettingsRouteSync = () => {
  const route = useRoute();
  const router = useRouter();

  const replaceSettingsQuery = (updates: SettingsRouteUpdates): void => {
    void router.replace({
      path: '/settings',
      query: buildSettingsQuery(route.query, updates),
    });
  };

  return {
    route,
    replaceSettingsQuery,
  };
};

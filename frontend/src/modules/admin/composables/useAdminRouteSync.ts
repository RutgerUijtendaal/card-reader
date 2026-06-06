import { useRoute, useRouter } from 'vue-router';
import { buildAdminQuery, type AdminTab } from '@/composables/admin/adminRouteState';
import type { CatalogKind } from '@/modules/admin/types';

type AdminRouteUpdates = {
  tab?: AdminTab | null;
  kind?: CatalogKind | null;
  entryId?: string | null;
};

export const useAdminRouteSync = () => {
  const route = useRoute();
  const router = useRouter();

  const replaceAdminQuery = (updates: AdminRouteUpdates): void => {
    void router.replace({
      path: '/admin',
      query: buildAdminQuery(route.query, updates),
    });
  };

  return {
    route,
    replaceAdminQuery,
  };
};

import { useRoute, useRouter } from 'vue-router';
import { buildAdminQuery, type AdminTab } from '@/features/admin/routeState';
import type { CatalogKind } from '@/features/admin/types';

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

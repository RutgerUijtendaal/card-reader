import type {
  LocationQueryRaw,
  RouteLocationNormalizedLoaded,
  RouteLocationRaw,
} from 'vue-router';
import type { CardPool } from '@/domain/cards/cardPools';
import { buildWorkspaceGalleryLocation } from '@/domain/cards/cardPoolWorkspace';

export type WorkspaceRouteCapability = 'global' | 'gallery' | 'resource' | 'player-only';

declare module 'vue-router' {
  interface RouteMeta {
    workspaceCapability?: WorkspaceRouteCapability;
  }
}

export type WorkspaceSelectionDecision =
  | { kind: 'reject' }
  | { kind: 'stay' }
  | {
      kind: 'replace-gallery' | 'update-resource-context' | 'fallback-gallery';
      location: RouteLocationRaw;
      navigation: 'push' | 'replace';
    };

type WorkspaceRoute = Pick<RouteLocationNormalizedLoaded, 'hash' | 'meta' | 'path' | 'query'>;

const buildSelectionGalleryLocation = (cardPool: CardPool): RouteLocationRaw =>
  cardPool === 'player'
    ? { path: '/cards', query: { card_pool: 'player' } }
    : buildWorkspaceGalleryLocation(cardPool);

const buildResourceWorkspaceLocation = (
  route: WorkspaceRoute,
  cardPool: CardPool,
): RouteLocationRaw => {
  const query: LocationQueryRaw = {
    ...route.query,
    return_card_pool: cardPool,
  };
  return {
    path: route.path,
    query,
    hash: route.hash,
  };
};

export const resolveWorkspaceSelectionDecision = (
  route: WorkspaceRoute,
  requestedPool: CardPool,
  activePool: CardPool,
  accessiblePools: readonly CardPool[],
): WorkspaceSelectionDecision => {
  if (!accessiblePools.includes(requestedPool)) {
    return { kind: 'reject' };
  }
  if (requestedPool === activePool) {
    return { kind: 'stay' };
  }

  switch (route.meta.workspaceCapability) {
    case 'global':
      return { kind: 'stay' };
    case 'gallery':
      return {
        kind: 'replace-gallery',
        location: buildSelectionGalleryLocation(requestedPool),
        navigation: 'replace',
      };
    case 'resource':
      return {
        kind: 'update-resource-context',
        location: buildResourceWorkspaceLocation(route, requestedPool),
        navigation: 'replace',
      };
    case 'player-only':
      if (requestedPool === 'player') {
        return { kind: 'stay' };
      }
      return {
        kind: 'fallback-gallery',
        location: buildSelectionGalleryLocation(requestedPool),
        navigation: 'push',
      };
    default:
      return { kind: 'reject' };
  }
};

import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw, RouterHistory } from 'vue-router';
import { useAuthStore } from '@/domain/session/store';
import LoginPage from '@/features/auth/LoginPage.vue';
import PasswordSetupPage from '@/features/auth/PasswordSetupPage.vue';
import ImportJobsPage from '@/features/import-jobs/ImportJobsPage.vue';
import OperationsPage from '@/features/operations/OperationsPage.vue';
import CardGalleryPage from '@/features/card-gallery/CardGalleryPage.vue';
import CardGroupDetailPage from '@/features/card-groups/CardGroupDetailPage.vue';
import CardDetailPage from '@/features/card-detail/CardDetailPage.vue';
import CardPublicDetailPage from '@/features/card-detail/CardPublicDetailPage.vue';
import DeckDetailPage from '@/features/decks/DeckDetailPage.vue';
import DeckEditorPage from '@/features/decks/DeckEditorPage.vue';
import DeckIndexPage from '@/features/decks/DeckIndexPage.vue';
import PlaytesterPage from '@/features/playtester/PlaytesterPage.vue';
import NotificationsPage from '@/features/notifications/NotificationsPage.vue';
import ReviewQueuePage from '@/features/review-queue/ReviewQueuePage.vue';
import SettingsPage from '@/features/settings/SettingsPage.vue';
import AdminPage from '@/features/admin/AdminPage.vue';
import { isCardPool, type CardPool } from '@/domain/cards/cardPools';
import {
  buildWorkspaceGalleryLocation,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';

const APP_TITLE = "Maity's Card Game";
const buildDocumentTitle = (pageTitle?: string): string => (pageTitle ? `${pageTitle} | ${APP_TITLE}` : APP_TITLE);

export const APP_ROUTES: RouteRecordRaw[] = [
  { path: '/', redirect: '/cards' },
  { path: '/cards', component: CardGalleryPage, meta: { workspaceCapability: 'gallery', title: 'Gallery' } },
  { path: '/cards/:id', component: CardPublicDetailPage, props: true, meta: { workspaceCapability: 'resource', title: 'Card' } },
  { path: '/card-groups/:id', component: CardGroupDetailPage, props: true, meta: { workspaceCapability: 'resource', title: 'Card Group' } },
  { path: '/decks', component: DeckIndexPage, meta: { title: 'Decks', workspaceCapability: 'player-only' } },
  { path: '/decks/:id', component: DeckDetailPage, props: true, meta: { title: 'Deck', workspaceCapability: 'player-only' } },
  { path: '/playtester', component: PlaytesterPage, meta: { title: 'Playtester', workspaceCapability: 'player-only' } },
  { path: '/playtester/:deckId', component: PlaytesterPage, meta: { title: 'Playtester', workspaceCapability: 'player-only' } },
  { path: '/login', component: LoginPage, meta: { public: true, title: 'Sign In', workspaceCapability: 'global' } },
  { path: '/password-setup', component: PasswordSetupPage, meta: { public: true, title: 'Password Setup', workspaceCapability: 'global' } },
  { path: '/my/decks', component: DeckIndexPage, meta: { requiresAuth: true, workspaceCapability: 'player-only', title: 'My Decks' } },
  { path: '/my/decks/:id', component: DeckDetailPage, meta: { requiresAuth: true, workspaceCapability: 'player-only', title: 'My Deck' }, props: true },
  { path: '/my/decks/new', component: DeckEditorPage, meta: { requiresAuth: true, workspaceCapability: 'player-only', title: 'New Deck' } },
  { path: '/my/decks/:id/edit', component: DeckEditorPage, meta: { requiresAuth: true, workspaceCapability: 'player-only', title: 'Edit Deck' }, props: true },
  { path: '/notifications', component: NotificationsPage, meta: { requiresAuth: true, title: 'Notifications', workspaceCapability: 'global' } },
  { path: '/settings', component: SettingsPage, meta: { title: 'Settings', workspaceCapability: 'global' } },
  { path: '/imports', component: ImportJobsPage, meta: { requiresStaff: true, title: 'Imports', workspaceCapability: 'global' } },
  { path: '/operations', component: OperationsPage, meta: { requiresStaff: true, title: 'Operations', workspaceCapability: 'global' } },
  { path: '/import-jobs', redirect: '/imports' },
  { path: '/cards/:id/edit', component: CardDetailPage, props: true, meta: { workspaceCapability: 'resource', requiresStaff: true, title: 'Edit Card' } },
  { path: '/review', component: ReviewQueuePage, meta: { requiresStaff: true, title: 'Review Queue', workspaceCapability: 'global' } },
  { path: '/admin', component: AdminPage, meta: { requiresStaff: true, title: 'Admin', workspaceCapability: 'global' } },
];

const resolveRouteWorkspacePool = (
  path: string,
  workspaceCapability: unknown,
  cardPool: unknown,
  returnCardPool: unknown,
): CardPool | undefined => {
  if (path === '/cards') {
    return isCardPool(cardPool) ? cardPool : undefined;
  }
  if (workspaceCapability !== 'resource') {
    return undefined;
  }
  if (isCardPool(returnCardPool)) {
    return returnCardPool;
  }
  return isCardPool(cardPool) ? cardPool : undefined;
};

export const createAppRouter = (history: RouterHistory = createWebHistory()) => {
  const router = createRouter({
    history,
    routes: APP_ROUTES,
  });

  router.beforeEach(async (to) => {
    const auth = useAuthStore();
    if (!auth.initialized) {
      await auth.fetchCurrentUser();
    }
    const workspace = useCardPoolWorkspaceStore();
    const rawRequestedPool = to.query.card_pool;
    const requestedPool = isCardPool(rawRequestedPool) ? rawRequestedPool : undefined;
    const sessionKey = auth.authenticated
      ? `user:${auth.user?.id ?? auth.user?.username ?? 'authenticated'}`
      : 'anonymous';
    workspace.synchronizeSession(auth.accessibleCardPools, sessionKey);

    if (to.meta.requiresAuth && !auth.authenticated) {
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      };
    }

    if (to.meta.requiresStaff && !auth.canAccessStaffRoutes) {
      if (auth.authenticated) {
        return '/cards';
      }
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      };
    }

    if (to.meta.workspaceCapability === 'player-only') {
      if (rawRequestedPool !== undefined) {
        const query = { ...to.query };
        delete query.card_pool;
        return { path: to.path, query, hash: to.hash };
      }
    }

    if (to.meta.workspaceCapability === 'resource') {
      const resourcePool = isCardPool(rawRequestedPool) ? rawRequestedPool : undefined;
      if (resourcePool && !workspace.accessiblePools.includes(resourcePool)) {
        return buildWorkspaceGalleryLocation('player');
      }
      const returnPool = isCardPool(to.query.return_card_pool)
        ? to.query.return_card_pool
        : undefined;
      if (returnPool && !workspace.accessiblePools.includes(returnPool)) {
        const query = { ...to.query };
        delete query.return_card_pool;
        return { path: to.path, query, hash: to.hash };
      }
    }

    const routeWorkspacePool = resolveRouteWorkspacePool(
      to.path,
      to.meta.workspaceCapability,
      rawRequestedPool,
      to.query.return_card_pool,
    );
    if (routeWorkspacePool && !workspace.accessiblePools.includes(routeWorkspacePool)) {
      return buildWorkspaceGalleryLocation('player');
    }

    if (to.path === '/cards') {
      if (requestedPool === 'player' && rawRequestedPool !== undefined) {
        return buildWorkspaceGalleryLocation('player', to.query);
      }
      if (rawRequestedPool !== undefined && requestedPool === undefined) {
        return buildWorkspaceGalleryLocation('player', to.query);
      }
      const redirectedFromExplicitPool = to.redirectedFrom?.path === '/cards'
        && to.redirectedFrom.query.card_pool !== undefined;
      if (
        rawRequestedPool === undefined
        && !redirectedFromExplicitPool
        && workspace.activePool !== 'player'
      ) {
        return buildWorkspaceGalleryLocation(workspace.activePool, to.query);
      }
    }

    if (to.path === '/login' && auth.canAccessStaffRoutes) {
      return '/operations';
    }

    return true;
  });

  router.afterEach((to, _from, failure) => {
    if (failure) {
      return;
    }
    const workspace = useCardPoolWorkspaceStore();
    let acceptedWorkspacePool: CardPool | undefined;
    if (to.meta.workspaceCapability === 'gallery') {
      acceptedWorkspacePool = isCardPool(to.query.card_pool) ? to.query.card_pool : 'player';
    } else if (to.meta.workspaceCapability === 'player-only') {
      acceptedWorkspacePool = 'player';
    } else if (to.meta.workspaceCapability === 'resource') {
      acceptedWorkspacePool = resolveRouteWorkspacePool(
        to.path,
        to.meta.workspaceCapability,
        to.query.card_pool,
        to.query.return_card_pool,
      );
    }
    if (acceptedWorkspacePool) {
      workspace.selectPool(acceptedWorkspacePool);
    }

    if (typeof document === 'undefined') {
      return;
    }

    document.title = buildDocumentTitle(typeof to.meta.title === 'string' ? to.meta.title : undefined);
  });

  return router;
};

export const router = createAppRouter();

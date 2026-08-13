import { createRouter, createWebHistory } from 'vue-router';
import type { RouterHistory } from 'vue-router';
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
import { isCardPool } from '@/domain/cards/cardPools';
import {
  buildWorkspaceGalleryLocation,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';

const APP_TITLE = "Maity's Card Game";
const buildDocumentTitle = (pageTitle?: string): string => (pageTitle ? `${pageTitle} | ${APP_TITLE}` : APP_TITLE);

export const createAppRouter = (history: RouterHistory = createWebHistory()) => {
  const router = createRouter({
    history,
    routes: [
      { path: '/', redirect: '/cards' },
      { path: '/cards', component: CardGalleryPage, meta: { cardPoolWorkspace: true, title: 'Gallery' } },
      { path: '/cards/:id', component: CardPublicDetailPage, props: true, meta: { cardPoolWorkspace: true, title: 'Card' } },
      { path: '/card-groups/:id', component: CardGroupDetailPage, props: true, meta: { cardPoolWorkspace: true, title: 'Card Group' } },
      { path: '/decks', component: DeckIndexPage, meta: { title: 'Decks', playerWorkspace: true } },
      { path: '/decks/:id', component: DeckDetailPage, props: true, meta: { title: 'Deck', playerWorkspace: true } },
      { path: '/playtester', component: PlaytesterPage, meta: { title: 'Playtester', playerWorkspace: true } },
      { path: '/playtester/:deckId', component: PlaytesterPage, meta: { title: 'Playtester', playerWorkspace: true } },
      { path: '/login', component: LoginPage, meta: { public: true, title: 'Sign In' } },
      { path: '/password-setup', component: PasswordSetupPage, meta: { public: true, title: 'Password Setup' } },
      { path: '/my/decks', component: DeckIndexPage, meta: { requiresAuth: true, playerWorkspace: true, title: 'My Decks' } },
      { path: '/my/decks/:id', component: DeckDetailPage, meta: { requiresAuth: true, playerWorkspace: true, title: 'My Deck' }, props: true },
      { path: '/my/decks/new', component: DeckEditorPage, meta: { requiresAuth: true, playerWorkspace: true, title: 'New Deck' } },
      { path: '/my/decks/:id/edit', component: DeckEditorPage, meta: { requiresAuth: true, playerWorkspace: true, title: 'Edit Deck' }, props: true },
      { path: '/notifications', component: NotificationsPage, meta: { requiresAuth: true, title: 'Notifications' } },
      { path: '/settings', component: SettingsPage, meta: { title: 'Settings' } },
      { path: '/imports', component: ImportJobsPage, meta: { requiresStaff: true, title: 'Imports' } },
      { path: '/operations', component: OperationsPage, meta: { requiresStaff: true, title: 'Operations' } },
      { path: '/import-jobs', redirect: '/imports' },
      { path: '/cards/:id/edit', component: CardDetailPage, props: true, meta: { cardPoolWorkspace: true, requiresStaff: true, title: 'Edit Card' } },
      { path: '/review', component: ReviewQueuePage, meta: { requiresStaff: true, title: 'Review Queue' } },
      { path: '/admin', component: AdminPage, meta: { requiresStaff: true, title: 'Admin' } },
    ],
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
    workspace.synchronizeSession(
      auth.accessibleCardPools,
      sessionKey,
      to.path === '/cards' ? requestedPool : undefined,
    );

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

    if (to.meta.playerWorkspace) {
      if (workspace.activePool !== 'player') {
        workspace.selectPool('player');
      }
      if (rawRequestedPool !== undefined) {
        const query = { ...to.query };
        delete query.card_pool;
        return { path: to.path, query, hash: to.hash };
      }
    }

    if (requestedPool && !workspace.accessiblePools.includes(requestedPool)) {
      workspace.selectPool('player');
      return buildWorkspaceGalleryLocation('player');
    }

    if (to.path === '/cards') {
      if (requestedPool === 'player' && rawRequestedPool !== undefined) {
        return buildWorkspaceGalleryLocation('player', to.query);
      }
      if (rawRequestedPool !== undefined && requestedPool === undefined) {
        workspace.selectPool('player');
        return buildWorkspaceGalleryLocation('player', to.query);
      }
      const representedPool = requestedPool ?? 'player';
      if (representedPool !== workspace.activePool) {
        return buildWorkspaceGalleryLocation(workspace.activePool, to.query);
      }
    }

    if (to.path === '/login' && auth.canAccessStaffRoutes) {
      return '/operations';
    }

    return true;
  });

  router.afterEach((to) => {
    if (typeof document === 'undefined') {
      return;
    }

    document.title = buildDocumentTitle(typeof to.meta.title === 'string' ? to.meta.title : undefined);
  });

  return router;
};

export const router = createAppRouter();

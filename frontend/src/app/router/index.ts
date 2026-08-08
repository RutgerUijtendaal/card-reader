import { createRouter, createWebHistory } from 'vue-router';
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

const APP_TITLE = "Maity's Card Game";
const buildDocumentTitle = (pageTitle?: string): string => (pageTitle ? `${pageTitle} | ${APP_TITLE}` : APP_TITLE);

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/cards' },
    { path: '/cards', component: CardGalleryPage, meta: { title: 'Gallery' } },
    { path: '/cards/:id', component: CardPublicDetailPage, props: true, meta: { title: 'Card' } },
    { path: '/card-groups/:id', component: CardGroupDetailPage, props: true, meta: { title: 'Card Group' } },
    { path: '/decks', component: DeckIndexPage, meta: { title: 'Decks' } },
    { path: '/decks/:id', component: DeckDetailPage, props: true, meta: { title: 'Deck' } },
    { path: '/playtester', component: PlaytesterPage, meta: { title: 'Playtester' } },
    { path: '/playtester/:deckId', component: PlaytesterPage, meta: { title: 'Playtester' } },
    { path: '/login', component: LoginPage, meta: { public: true, title: 'Sign In' } },
    { path: '/password-setup', component: PasswordSetupPage, meta: { public: true, title: 'Password Setup' } },
    { path: '/my/decks', component: DeckIndexPage, meta: { requiresAuth: true, title: 'My Decks' } },
    { path: '/my/decks/:id', component: DeckDetailPage, meta: { requiresAuth: true, title: 'My Deck' }, props: true },
    { path: '/my/decks/new', component: DeckEditorPage, meta: { requiresAuth: true, title: 'New Deck' } },
    { path: '/my/decks/:id/edit', component: DeckEditorPage, meta: { requiresAuth: true, title: 'Edit Deck' }, props: true },
    { path: '/notifications', component: NotificationsPage, meta: { requiresAuth: true, title: 'Notifications' } },
    { path: '/settings', component: SettingsPage, meta: { title: 'Settings' } },
    { path: '/imports', component: ImportJobsPage, meta: { requiresStaff: true, title: 'Imports' } },
    { path: '/operations', component: OperationsPage, meta: { requiresStaff: true, title: 'Operations' } },
    { path: '/import-jobs', redirect: '/imports' },
    { path: '/cards/:id/edit', component: CardDetailPage, props: true, meta: { requiresStaff: true, title: 'Edit Card' } },
    { path: '/review', component: ReviewQueuePage, meta: { requiresStaff: true, title: 'Review Queue' } },
    { path: '/admin', component: AdminPage, meta: { requiresStaff: true, title: 'Admin' } },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.initialized) {
    await auth.fetchCurrentUser();
  }

  if (to.path === '/login' && auth.canAccessStaffRoutes) {
    return '/operations';
  }

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

  return true;
});

router.afterEach((to) => {
  if (typeof document === 'undefined') {
    return;
  }

  document.title = buildDocumentTitle(typeof to.meta.title === 'string' ? to.meta.title : undefined);
});

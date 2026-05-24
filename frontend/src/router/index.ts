import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/modules/auth/authStore';
import LoginPage from '@/modules/auth/LoginPage.vue';
import PasswordSetupPage from '@/modules/auth/PasswordSetupPage.vue';
import ImportJobsPage from '@/modules/import-jobs/ImportJobsPage.vue';
import CardSearchPage from '@/modules/card-search/CardSearchPage.vue';
import CardGroupDetailPage from '@/modules/card-groups/CardGroupDetailPage.vue';
import CardDetailPage from '@/modules/card-detail/CardDetailPage.vue';
import CardPublicDetailPage from '@/modules/card-detail/CardPublicDetailPage.vue';
import DeckBrowsePage from '@/modules/decks/DeckBrowsePage.vue';
import DeckDetailPage from '@/modules/decks/DeckDetailPage.vue';
import DeckEditorPage from '@/modules/decks/DeckEditorPage.vue';
import MyDecksPage from '@/modules/decks/MyDecksPage.vue';
import ReviewQueuePage from '@/modules/review-queue/ReviewQueuePage.vue';
import AdminPage from '@/modules/admin/AdminPage.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/cards' },
    { path: '/cards', component: CardSearchPage },
    { path: '/cards/:id', component: CardPublicDetailPage, props: true },
    { path: '/card-groups/:id', component: CardGroupDetailPage, props: true },
    { path: '/decks', component: DeckBrowsePage },
    { path: '/decks/:id', component: DeckDetailPage, props: true },
    { path: '/login', component: LoginPage, meta: { public: true } },
    { path: '/password-setup', component: PasswordSetupPage, meta: { public: true } },
    { path: '/my/decks', component: MyDecksPage, meta: { requiresAuth: true } },
    { path: '/my/decks/new', component: DeckEditorPage, meta: { requiresAuth: true } },
    { path: '/my/decks/:id/edit', component: DeckEditorPage, meta: { requiresAuth: true }, props: true },
    { path: '/import-jobs', component: ImportJobsPage, meta: { requiresStaff: true } },
    { path: '/cards/:id/edit', component: CardDetailPage, props: true, meta: { requiresStaff: true } },
    { path: '/review', component: ReviewQueuePage, meta: { requiresStaff: true } },
    { path: '/admin', component: AdminPage, meta: { requiresStaff: true } },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.initialized) {
    await auth.fetchCurrentUser();
  }

  if (to.path === '/login' && auth.canAccessStaffRoutes) {
    return '/import-jobs';
  }

  if (to.meta.requiresAuth && auth.authEnabled && !auth.authenticated) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    };
  }

  if (to.meta.requiresStaff && !auth.canAccessStaffRoutes) {
    if (auth.authEnabled && auth.authenticated) {
      return '/cards';
    }
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    };
  }

  return true;
});

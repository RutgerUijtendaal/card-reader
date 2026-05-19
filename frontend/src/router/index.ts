import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/modules/auth/authStore';
import LoginPage from '@/modules/auth/LoginPage.vue';
import ImportJobsPage from '@/modules/import-jobs/ImportJobsPage.vue';
import CardSearchPage from '@/modules/card-search/CardSearchPage.vue';
import CardDetailPage from '@/modules/card-detail/CardDetailPage.vue';
import CardPublicDetailPage from '@/modules/card-detail/CardPublicDetailPage.vue';
import ReviewQueuePage from '@/modules/review-queue/ReviewQueuePage.vue';
import SettingsPage from '@/modules/settings/SettingsPage.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/cards' },
    { path: '/cards', component: CardSearchPage },
    { path: '/cards/:id', component: CardPublicDetailPage, props: true },
    { path: '/login', component: LoginPage, meta: { public: true } },
    { path: '/import-jobs', component: ImportJobsPage, meta: { requiresStaff: true } },
    { path: '/cards/:id/edit', component: CardDetailPage, props: true, meta: { requiresStaff: true } },
    { path: '/review', component: ReviewQueuePage, meta: { requiresStaff: true } },
    { path: '/settings', component: SettingsPage, meta: { requiresStaff: true } },
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

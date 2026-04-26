import { createRouter, createWebHistory } from 'vue-router';
import ImportJobsPage from '@/modules/import-jobs/ImportJobsPage.vue';
import CardSearchPage from '@/modules/card-search/CardSearchPage.vue';
import CardDetailPage from '@/modules/card-detail/CardDetailPage.vue';
import ReviewQueuePage from '@/modules/review-queue/ReviewQueuePage.vue';
import SettingsPage from '@/modules/settings/SettingsPage.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/cards' },
    { path: '/cards', component: CardSearchPage },
    { path: '/import-jobs', component: ImportJobsPage },
    { path: '/cards/:id', component: CardDetailPage, props: true },
    { path: '/review', component: ReviewQueuePage },
    { path: '/settings', component: SettingsPage },
  ],
});

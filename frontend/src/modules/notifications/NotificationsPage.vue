<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="Bell"
      title="Notifications"
      subtitle="Review updates tied to your decks, submitted flags, and account activity."
      title-tag="h2"
      title-class="text-xl"
    />

    <AppPageLayout
      columns="one"
      root-class="app-page-layout-standard"
    >
      <template #aside>
        <AppStickyAside>
          <div class="mb-3 px-1">
            <h3 class="theme-section-title text-sm font-semibold">
              Inbox
            </h3>
            <p class="theme-section-muted mt-1 text-xs">
              {{ unreadNotificationCount }} unread notification{{ unreadNotificationCount === 1 ? '' : 's' }}.
            </p>
          </div>

          <nav
            class="flex flex-col gap-2"
            aria-label="Notification views"
          >
            <button
              v-for="option in statusOptions"
              :key="option.value"
              type="button"
              class="rounded-lg border px-3 py-3 text-left transition"
              :class="statusFilter === option.value
                ? 'theme-selected-surface-strong'
                : 'theme-card-frame theme-section-title hover:border-[var(--theme-border-strong)]'"
              @click="selectStatus(option.value)"
            >
              <div class="flex items-start justify-between gap-3">
                <span class="min-w-0">
                  <span class="block truncate text-sm font-semibold">{{ option.label }}</span>
                  <span
                    class="mt-1 block truncate text-xs"
                    :class="statusFilter === option.value ? 'theme-section-title' : 'theme-section-muted'"
                  >
                    {{ option.description }}
                  </span>
                </span>
                <span
                  v-if="option.value === 'unread' && unreadNotificationCount > 0"
                  class="theme-pill theme-pill-warning shrink-0 px-2 py-0.5 text-[11px] font-semibold"
                >
                  {{ unreadNotificationCount }}
                </span>
              </div>
            </button>
          </nav>
        </AppStickyAside>
      </template>

      <section class="pt-0">
        <div class="theme-divider mb-4 flex flex-wrap items-start justify-between gap-3 border-b pb-4">
          <div class="min-w-0">
            <h3 class="theme-section-title text-base font-semibold">
              {{ activeStatusOption.label }}
            </h3>
            <p class="theme-section-muted mt-1 text-sm">
              {{ activeStatusOption.description }}
            </p>
          </div>
          <button
            v-if="statusFilter === 'unread'"
            type="button"
            class="btn-secondary inline-flex shrink-0 items-center gap-2"
            :disabled="unreadNotificationCount === 0 || markingAllRead"
            @click="handleMarkAllRead"
          >
            <CheckCheck class="h-4 w-4" />
            <span>Mark all read</span>
          </button>
        </div>

        <div
          v-if="!notificationsLoaded"
          class="theme-divider"
        >
          <article
            v-for="index in 4"
            :key="`notification-loading-${index}`"
            class="notification-row theme-divider py-4"
          >
            <div class="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div class="min-w-0 flex-1 space-y-3">
                <div class="flex items-center gap-2">
                  <span class="h-2 w-2 shrink-0 animate-pulse rounded-full bg-[var(--color-surface-muted)]" />
                  <span class="h-4 w-2/5 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                  <span class="h-5 w-8 animate-pulse rounded-full bg-[var(--color-surface-muted)]" />
                </div>
                <div class="h-4 w-4/5 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                <div class="h-3 w-32 animate-pulse rounded bg-[var(--color-surface-muted)]" />
              </div>

              <div class="h-9 w-24 shrink-0 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
            </div>
          </article>
        </div>

        <div
          v-else-if="errorMessage"
          class="page-card theme-section-muted text-sm"
        >
          {{ errorMessage }}
        </div>

        <div
          v-else-if="notifications.length === 0"
          class="theme-section-muted flex min-h-72 items-center justify-center py-10 text-center text-sm"
        >
          <div class="space-y-1">
            <h3 class="theme-section-title text-sm font-semibold">
              {{ emptyState.title }}
            </h3>
            <p class="mx-auto max-w-md leading-6">
              {{ emptyState.message }}
            </p>
          </div>
        </div>

        <div
          v-else
          class="theme-divider"
        >
          <article
            v-for="notification in notifications"
            :key="notification.id"
            class="notification-row theme-divider py-4"
            :class="notification.read_at ? 'notification-row-read' : 'notification-row-unread'"
          >
            <div class="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <RouterLink
                class="min-w-0 flex-1"
                :to="notification.target_url || '/notifications'"
                @click="handleNotificationOpen(notification)"
              >
                <div class="flex min-w-0 flex-wrap items-center gap-2">
                  <span
                    v-if="!notification.read_at"
                    class="notification-unread-dot"
                    aria-hidden="true"
                  />
                  <h3 class="theme-section-title min-w-0 truncate text-sm font-semibold">
                    {{ notification.title }}
                  </h3>
                  <span
                    v-if="notification.event_count > 1"
                    class="theme-pill theme-pill-warning px-2 py-0.5 text-[11px] font-semibold"
                  >
                    {{ notification.event_count }}
                  </span>
                </div>
                <p class="theme-section-muted mt-1 text-sm">
                  {{ notification.message }}
                </p>
                <p class="theme-section-muted mt-2 text-xs">
                  {{ formatNotificationDate(notification.last_event_at) }}
                </p>
              </RouterLink>

              <button
                type="button"
                class="btn-secondary shrink-0"
                :disabled="updatingIds.has(notification.id)"
                @click="toggleReadState(notification)"
              >
                {{ notification.read_at ? 'Mark unread' : 'Mark read' }}
              </button>
            </div>
          </article>
        </div>
      </section>
    </AppPageLayout>

    <footer
      v-if="page.previous_page || page.next_page"
      class="theme-divider app-page-content app-page-layout-standard flex w-full flex-wrap items-center justify-between gap-3 border-t !py-0 !pt-4"
    >
      <button
        type="button"
        class="btn-secondary"
        :disabled="!page.previous_page || loading"
        @click="loadPage(page.previous_page)"
      >
        Previous
      </button>
      <span class="theme-section-muted text-sm">Page {{ page.page }}</span>
      <button
        type="button"
        class="btn-secondary"
        :disabled="!page.next_page || loading"
        @click="loadPage(page.next_page)"
      >
        Next
      </button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { Bell, CheckCheck } from 'lucide-vue-next';
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { RouterLink } from 'vue-router';
import AppPageLayout from '@/components/app/AppPageLayout.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppStickyAside from '@/components/app/AppStickyAside.vue';
import { useNotificationSummary } from '@/composables/useNotificationSummary';
import {
  buildNotificationSearchParams,
  fetchNotifications,
  markAllNotificationsRead,
  setNotificationReadState,
} from '@/modules/notifications/api';
import type { NotificationPage, NotificationStatusFilter, UserNotification } from '@/modules/notifications/types';

const statusOptions: Array<{ value: NotificationStatusFilter; label: string; description: string }> = [
  { value: 'unread', label: 'Unread', description: 'Updates that still need attention.' },
  { value: 'all', label: 'All', description: 'Complete notification history.' },
];
const pageSize = 25;
const statusFilter = ref<NotificationStatusFilter>('unread');
const notifications = ref<UserNotification[]>([]);
const notificationsLoaded = ref(false);
const page = ref<NotificationPage>({
  count: 0,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: pageSize,
  results: [],
});
const loading = ref(false);
const markingAllRead = ref(false);
const errorMessage = ref('');
const updatingIds = ref(new Set<string>());
const { unreadNotificationCount, loadNotificationSummary, setUnreadNotificationCount } = useNotificationSummary();
const activeStatusOption = computed(
  () => statusOptions.find((option) => option.value === statusFilter.value) ?? statusOptions[0],
);

const emptyState = computed<{ title: string; message: string }>(() => {
  if (statusFilter.value === 'unread') {
    return {
      title: "You're all caught up",
      message: 'Card changes and flag review updates will show up here when they need your attention.',
    };
  }
  return {
    title: 'No notifications yet',
    message: 'Updates about your decks and submitted flags will appear here.',
  };
});

const loadNotifications = async (nextPage = 1): Promise<void> => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const response = await fetchNotifications(buildNotificationSearchParams(statusFilter.value, nextPage, pageSize));
    page.value = response;
    notifications.value = response.results;
  } catch {
    errorMessage.value = 'Unable to load notifications.';
    notifications.value = [];
  } finally {
    notificationsLoaded.value = true;
    loading.value = false;
  }
};

const selectStatus = (status: NotificationStatusFilter): void => {
  if (statusFilter.value === status) {
    return;
  }
  statusFilter.value = status;
};

const loadPage = (nextPage: number | null): void => {
  if (!nextPage) {
    return;
  }
  void loadNotifications(nextPage);
};

const toggleReadState = async (notification: UserNotification): Promise<void> => {
  updatingIds.value = new Set(updatingIds.value).add(notification.id);
  const nextReadState = notification.read_at === null;
  try {
    const updated = await setNotificationReadState(notification.id, nextReadState);
    notifications.value = notifications.value.map((entry) => (entry.id === updated.id ? updated : entry));
    await loadNotificationSummary();
    if (statusFilter.value !== 'all') {
      await loadNotifications(page.value.page);
    }
  } catch {
    toast.error('Unable to update notification.');
  } finally {
    const nextUpdatingIds = new Set(updatingIds.value);
    nextUpdatingIds.delete(notification.id);
    updatingIds.value = nextUpdatingIds;
  }
};

const handleNotificationOpen = (notification: UserNotification): void => {
  if (notification.read_at) {
    return;
  }
  void toggleReadState(notification);
};

const handleMarkAllRead = async (): Promise<void> => {
  markingAllRead.value = true;
  try {
    const response = await markAllNotificationsRead();
    setUnreadNotificationCount(response.unread_count);
    await loadNotifications(1);
  } catch {
    toast.error('Unable to mark notifications read.');
  } finally {
    markingAllRead.value = false;
  }
};

const formatNotificationDate = (value: string): string =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));

watch(statusFilter, () => {
  void loadNotifications(1);
});

onMounted(() => {
  void loadNotifications();
});
</script>

<style scoped>
.notification-row {
  border-left: 3px solid transparent;
  padding-left: 0.75rem;
}

.notification-row + .notification-row {
  border-top-width: 1px;
}

.notification-row-unread {
  border-left-color: var(--color-warning-text);
}

.notification-row-read {
  opacity: 0.82;
}

.notification-unread-dot {
  height: 0.5rem;
  width: 0.5rem;
  flex-shrink: 0;
  border-radius: 999px;
  background: var(--color-warning-text);
}

.notification-scroll-area {
  scrollbar-gutter: auto;
}

</style>

<template>
  <section class="flex h-[calc(100vh-3rem)] min-h-0 flex-col gap-5 overflow-hidden">
    <AppPageHeader
      :icon="Bell"
      title="Notifications"
      subtitle="Review updates tied to your decks, submitted flags, and account activity."
      title-tag="h2"
      title-class="text-xl"
    />

    <div class="mx-auto grid min-h-0 w-full max-w-5xl flex-1 gap-5 overflow-hidden lg:grid-cols-[16rem_minmax(0,42rem)]">
      <aside class="flex min-h-0 flex-col overflow-hidden">
        <div class="mb-3 px-1">
          <h3 class="theme-section-title text-sm font-semibold">
            Inbox
          </h3>
          <p class="theme-section-muted mt-1 text-xs">
            {{ unreadNotificationCount }} unread notification{{ unreadNotificationCount === 1 ? '' : 's' }}.
          </p>
        </div>

        <nav
          class="app-scrollbar flex min-h-0 flex-col gap-2 overflow-y-auto pr-1"
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
      </aside>

      <section class="theme-divider app-scrollbar min-h-0 overflow-y-auto border-t pt-5 lg:border-l lg:border-t-0 lg:py-1 lg:pl-6">
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
          v-if="loading"
          class="grid gap-3"
        >
          <div
            v-for="index in 4"
            :key="`notification-loading-${index}`"
            class="page-card animate-pulse space-y-3"
          >
            <div class="h-4 w-2/5 rounded bg-[var(--color-surface-muted)]" />
            <div class="h-3 w-4/5 rounded bg-[var(--color-surface-muted)]" />
          </div>
        </div>

        <div
          v-else-if="errorMessage"
          class="page-card theme-section-muted text-sm"
        >
          {{ errorMessage }}
        </div>

        <div
          v-else-if="notifications.length === 0"
          class="notification-empty-state theme-section-muted"
        >
          <div
            class="notification-empty-state-icon"
            aria-hidden="true"
          >
            <component
              :is="emptyState.icon"
              class="h-7 w-7"
            />
          </div>
          <div class="space-y-1 text-center">
            <h3 class="theme-section-title text-sm font-semibold">
              {{ emptyState.title }}
            </h3>
            <p class="mx-auto max-w-md text-sm leading-6">
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
    </div>

    <footer
      v-if="page.previous_page || page.next_page"
      class="theme-divider mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-3 border-t pt-4"
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
import { BadgeCheck, Bell, CheckCheck, Inbox } from 'lucide-vue-next';
import type { Component } from 'vue';
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { RouterLink } from 'vue-router';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
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

const emptyState = computed<{ icon: Component; title: string; message: string }>(() => {
  if (statusFilter.value === 'unread') {
    return {
      icon: BadgeCheck,
      title: "You're all caught up",
      message: 'Card changes and flag review updates will show up here when they need your attention.',
    };
  }
  return {
    icon: Inbox,
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

.notification-empty-state {
  display: flex;
  min-height: 18rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem;
}

.notification-empty-state-icon {
  display: flex;
  height: 3rem;
  width: 3rem;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}
</style>

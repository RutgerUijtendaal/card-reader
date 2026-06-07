<template>
  <section class="flex h-[calc(100vh-3rem)] min-h-0 flex-col gap-5 overflow-hidden">
    <AppPageHeader
      :icon="Bell"
      title="Notifications"
      subtitle="Review updates tied to your decks, submitted flags, and account activity."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <button
          type="button"
          class="btn-secondary inline-flex items-center gap-2"
          :disabled="unreadNotificationCount === 0 || markingAllRead"
          @click="handleMarkAllRead"
        >
          <CheckCheck class="h-4 w-4" />
          <span>Mark all read</span>
        </button>
      </template>
      <template #bottomLeft>
        <span class="theme-section-muted text-sm">{{ unreadNotificationCount }} unread</span>
      </template>
      <template #bottomRight>
        <div class="theme-tablist">
          <button
            v-for="option in statusOptions"
            :key="option.value"
            type="button"
            class="theme-tab"
            :class="{ 'theme-tab-active': statusFilter === option.value }"
            @click="selectStatus(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </template>
    </AppPageHeader>

    <section class="min-h-0 flex-1 overflow-hidden">
      <div class="notification-scroll-area app-scrollbar h-full overflow-y-auto">
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
          class="theme-empty-state notification-empty-state"
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
          class="grid gap-3"
        >
          <article
            v-for="notification in notifications"
            :key="notification.id"
            class="page-card notification-row"
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
      </div>
    </section>

    <footer
      v-if="page.previous_page || page.next_page"
      class="theme-panel-shell flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3"
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

const statusOptions: Array<{ value: NotificationStatusFilter; label: string }> = [
  { value: 'unread', label: 'Unread' },
  { value: 'all', label: 'All' },
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
  height: 4rem;
  width: 4rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--color-border-strong) 75%, transparent);
  background: color-mix(in srgb, var(--color-surface-muted) 72%, transparent);
  color: var(--color-text-muted);
}
</style>

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
        <AppStickyAside scroll-class="space-y-4">
          <div class="px-1">
            <h3 class="theme-section-title text-sm font-semibold">
              Notification filters
            </h3>
            <p class="theme-section-muted mt-1 text-xs">
              Show the updates that matter right now. {{ unreadNotificationCount }} new.
            </p>
          </div>

          <nav
            class="flex flex-col gap-2"
            aria-label="Notification type filters"
          >
            <button
              v-for="option in typeOptions"
              :key="option.value"
              type="button"
              class="rounded-lg border px-3 py-3 text-left transition"
              :class="typeFilter === option.value
                ? 'theme-selected-surface-strong'
                : 'theme-card-frame theme-section-title hover:border-[var(--theme-border-strong)]'"
              @click="selectType(option.value)"
            >
              <div class="flex items-start gap-3">
                <component
                  :is="option.icon"
                  class="mt-0.5 h-4 w-4 shrink-0"
                />
                <span class="flex min-w-0 flex-1 items-start justify-between gap-3">
                  <span class="min-w-0">
                    <span class="block truncate text-sm font-semibold">{{ option.label }}</span>
                    <span
                      class="mt-1 block truncate text-xs"
                      :class="typeFilter === option.value ? 'theme-section-title' : 'theme-section-muted'"
                    >
                      {{ option.description }}
                    </span>
                  </span>
                </span>
              </div>
            </button>
          </nav>

          <template #footer>
            <GalleryOptionsMenu
              :hover-mode="effectiveHoverMode"
              :default-hover-mode="defaultHoverMode"
              :hover-mode-override-active="notificationHoverModeOverride !== null"
              allow-hover-mode-default-option
              :card-scale="cardScale"
              :show-card-groups-control="false"
              @update:hover-mode="setNotificationHoverModeOverride"
              @reset:hover-mode="clearNotificationHoverModeOverride"
              @update:card-scale="cardScale = $event"
            />
          </template>
        </AppStickyAside>
      </template>

      <section class="pt-0">
        <div class="theme-divider mb-4 flex flex-wrap items-start justify-between gap-3 border-b pb-4">
          <div class="flex min-w-0 items-start gap-3">
            <div
              class="theme-card-frame-muted theme-section-title flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
              aria-hidden="true"
            >
              <component
                :is="activeTypeOption.icon"
                class="h-5 w-5"
              />
            </div>
            <div class="min-w-0">
              <h3 class="theme-section-title text-base font-semibold">
                {{ activeTypeOption.label }}
              </h3>
              <p class="theme-section-muted mt-1 text-sm">
                {{ notifications.length }} loaded · {{ page.count }} total
              </p>
            </div>
          </div>
          <button
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
          v-if="loadingInitial"
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

              <div class="flex w-full shrink-0 flex-col gap-2 sm:w-32">
                <div class="h-9 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
                <div class="h-9 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
              </div>
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
          <NotificationTimelineEntry
            v-for="notification in notifications"
            :key="notification.id"
            :notification="notification"
            @interact="handleNotificationInteraction"
          />
        </div>

        <div
          v-if="page.next_page"
          class="theme-divider flex justify-end border-t pt-4"
        >
          <button
            type="button"
            class="btn-secondary"
            :disabled="loadingMore"
            @click="loadMore"
          >
            {{ loadingMore ? 'Loading...' : 'Load more' }}
          </button>
        </div>
      </section>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { Bell, CheckCheck, Flag, Inbox, RefreshCw } from 'lucide-vue-next';
import { computed, onMounted, ref, watch } from 'vue';
import type { Component } from 'vue';
import { toast } from 'vue-sonner';
import AppPageLayout from '@/components/app/AppPageLayout.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppStickyAside from '@/components/app/AppStickyAside.vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import { useGalleryOptions } from '@/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/composables/useHoverModePreferences';
import { useNotificationSummary } from '@/composables/useNotificationSummary';
import {
  buildNotificationSearchParams,
  fetchNotifications,
  markAllNotificationsRead,
  setNotificationReadState,
} from '@/modules/notifications/api';
import NotificationTimelineEntry from '@/modules/notifications/components/NotificationTimelineEntry.vue';
import {
  NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED,
  NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
} from '@/modules/notifications/types';
import type { NotificationPage, UserNotification } from '@/modules/notifications/types';

type NotificationTypeFilter = 'all' | 'flag-review' | 'deck-card-update';
type NotificationTypeOption = {
  value: NotificationTypeFilter;
  label: string;
  description: string;
  icon: Component;
  eventType: string | null;
};

const typeOptions: NotificationTypeOption[] = [
  { value: 'all', label: 'All notifications', description: 'Every inbox update.', icon: Inbox, eventType: null },
  {
    value: 'flag-review',
    label: 'Flag reviews',
    description: 'Results for submitted flags.',
    icon: Flag,
    eventType: NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
  },
  {
    value: 'deck-card-update',
    label: 'Deck card updates',
    description: 'Card versions used by your decks.',
    icon: RefreshCw,
    eventType: NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED,
  },
];
const pageSize = 25;
const typeFilter = ref<NotificationTypeFilter>('all');
const notifications = ref<UserNotification[]>([]);
const page = ref<NotificationPage>({
  count: 0,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: pageSize,
  results: [],
});
const loadingInitial = ref(false);
const loadingMore = ref(false);
const markingAllRead = ref(false);
const errorMessage = ref('');
const updatingIds = ref(new Set<string>());
let latestLoadRequestId = 0;
const { unreadNotificationCount, setUnreadNotificationCount } = useNotificationSummary();
const { cardScale } = useGalleryOptions();
const {
  defaultHoverMode,
  overrideHoverMode: notificationHoverModeOverride,
  effectiveHoverMode,
  setOverrideHoverMode: setNotificationHoverModeOverride,
  clearOverrideHoverMode: clearNotificationHoverModeOverride,
} = useHoverModeSurface('notifications');
const activeTypeOption = computed(
  () => typeOptions.find((option) => option.value === typeFilter.value) ?? typeOptions[0],
);

const emptyState = computed<{ title: string; message: string }>(() => {
  if (typeFilter.value === 'flag-review') {
    return {
      title: 'No flag review notifications',
      message: 'Results for your submitted card flags will appear here.',
    };
  }
  if (typeFilter.value === 'deck-card-update') {
    return {
      title: 'No deck card updates',
      message: 'Changes to card versions used by your decks will appear here.',
    };
  }
  return {
    title: 'No notifications yet',
    message: 'Updates about your decks and submitted flags will appear here.',
  };
});

const loadNotifications = async (
  nextPage = 1,
  mode: 'replace' | 'append' = 'replace',
): Promise<void> => {
  const requestId = ++latestLoadRequestId;
  loadingInitial.value = mode === 'replace';
  loadingMore.value = mode === 'append';
  errorMessage.value = '';
  try {
    const response = await fetchNotifications(
      buildNotificationSearchParams(nextPage, pageSize, activeTypeOption.value.eventType),
    );
    if (requestId !== latestLoadRequestId) {
      return;
    }
    page.value = response;
    if (mode === 'replace') {
      notifications.value = response.results;
    } else {
      const knownIds = new Set(notifications.value.map((notification) => notification.id));
      notifications.value = [
        ...notifications.value,
        ...response.results.filter((notification) => !knownIds.has(notification.id)),
      ];
    }
  } catch {
    if (requestId !== latestLoadRequestId) {
      return;
    }
    errorMessage.value = 'Unable to load notifications.';
    if (mode === 'replace') {
      notifications.value = [];
    }
  } finally {
    if (requestId === latestLoadRequestId) {
      loadingInitial.value = false;
      loadingMore.value = false;
    }
  }
};

const selectType = (type: NotificationTypeFilter): void => {
  if (typeFilter.value === type) {
    return;
  }
  typeFilter.value = type;
};

const loadMore = (): void => {
  if (!page.value.next_page || loadingMore.value) {
    return;
  }
  void loadNotifications(page.value.next_page, 'append');
};

const handleNotificationInteraction = (notification: UserNotification): void => {
  if (notification.read_at || updatingIds.value.has(notification.id)) {
    return;
  }

  updatingIds.value = new Set(updatingIds.value).add(notification.id);
  const optimisticReadAt = new Date().toISOString();
  notifications.value = notifications.value.map((entry) =>
    entry.id === notification.id ? { ...entry, read_at: optimisticReadAt } : entry,
  );
  setUnreadNotificationCount(Math.max(0, unreadNotificationCount.value - 1));

  void setNotificationReadState(notification.id, true)
    .then((updated) => {
      notifications.value = notifications.value.map((entry) => (entry.id === updated.id ? updated : entry));
    })
    .catch(() => {
      notifications.value = notifications.value.map((entry) =>
        entry.id === notification.id ? { ...entry, read_at: null } : entry,
      );
      setUnreadNotificationCount(unreadNotificationCount.value + 1);
      toast.error('Unable to mark notification read.');
    })
    .finally(() => {
      const nextUpdatingIds = new Set(updatingIds.value);
      nextUpdatingIds.delete(notification.id);
      updatingIds.value = nextUpdatingIds;
    });
};

const handleMarkAllRead = async (): Promise<void> => {
  markingAllRead.value = true;
  try {
    const response = await markAllNotificationsRead();
    setUnreadNotificationCount(response.unread_count);
    const readAt = new Date().toISOString();
    notifications.value = notifications.value.map((notification) => ({
      ...notification,
      read_at: notification.read_at ?? readAt,
    }));
  } catch {
    toast.error('Unable to mark notifications read.');
  } finally {
    markingAllRead.value = false;
  }
};

watch(typeFilter, () => {
  void loadNotifications(1);
});

onMounted(() => {
  void loadNotifications();
});

</script>

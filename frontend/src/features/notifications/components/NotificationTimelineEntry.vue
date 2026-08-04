<template>
  <article
    class="notification-row theme-divider py-5"
    :class="notification.read_at ? 'notification-row-read' : 'notification-row-unread'"
    :data-notification-id="notification.id"
    @click="handleRowInteraction"
  >
    <div class="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div class="flex min-w-0 flex-1 items-start gap-3">
        <div
          class="theme-card-frame-muted theme-section-title mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
          aria-hidden="true"
        >
          <component
            :is="eventIcon"
            class="h-4 w-4"
          />
        </div>

        <div class="min-w-0 flex-1">
          <div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <span
              v-if="!notification.read_at"
              class="notification-unread-dot"
              aria-hidden="true"
            />
            <span class="theme-section-muted text-xs font-semibold uppercase tracking-wide">
              {{ presentation.category }}
            </span>
            <span
              v-if="presentation.status"
              class="theme-pill px-2 py-0.5 text-[11px] font-semibold capitalize"
              :class="presentation.status === 'resolved' ? 'theme-pill-success' : 'theme-pill-neutral'"
            >
              {{ presentation.status }}
            </span>
            <span class="theme-section-muted text-xs">
              {{ formattedDate }}
            </span>
          </div>

          <h3 class="theme-section-title mt-2 text-sm font-semibold leading-6">
            {{ presentation.title }}
          </h3>
          <p
            v-if="presentation.summary"
            class="theme-section-muted mt-1 text-sm leading-6"
          >
            {{ presentation.summary }}
          </p>
          <p
            v-if="presentation.occurrenceLabel"
            class="theme-section-muted mt-2 text-xs font-medium"
          >
            {{ presentation.occurrenceLabel }}
          </p>

          <button
            v-if="hasExpandableContent"
            class="notification-details-trigger theme-link mt-3 inline-flex items-center gap-1 text-sm font-semibold"
            type="button"
            :aria-expanded="detailsOpen"
            :aria-controls="detailsId"
            data-testid="notification-details-trigger"
            @click.stop="handleRowInteraction"
          >
            {{ presentation.detailsLabel }}
            <ChevronDown
              class="notification-details-chevron h-4 w-4"
              :class="detailsOpen ? 'notification-details-chevron-open' : ''"
            />
          </button>
        </div>
      </div>

      <div
        v-if="presentation.actions.length > 0"
        class="notification-actions flex shrink-0 items-center gap-2 self-end sm:self-start"
        data-testid="notification-actions"
      >
        <InfoTooltip
          v-for="action in presentation.actions"
          :key="action.label"
          v-slot="{ tooltipId }"
          :text="action.label"
          :trigger-tabbable="false"
        >
          <RouterLink
            class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-9 w-9 items-center justify-center rounded-lg"
            :to="action.to"
            :aria-label="action.label"
            :aria-describedby="tooltipId"
            @click.stop="handleAction"
          >
            <component
              :is="actionIcon(action.icon)"
              class="h-4 w-4"
              aria-hidden="true"
            />
          </RouterLink>
        </InfoTooltip>
      </div>
    </div>

    <div
      v-if="detailsOpen && hasExpandableContent"
      :id="detailsId"
      class="notification-details theme-divider ml-12 mt-3 border-t pt-3"
      data-testid="notification-details"
    >
      <dl
        v-if="presentation.details.length > 0"
        class="grid gap-3"
      >
        <div
          v-for="detail in presentation.details"
          :key="detail.label"
        >
          <dt class="theme-section-title text-xs font-semibold">
            {{ detail.label }}
          </dt>
          <dd class="theme-section-muted mt-1 whitespace-pre-wrap break-words text-sm leading-6">
            {{ detail.value }}
          </dd>
        </div>
      </dl>
      <NotificationCardVersionComparison
        v-if="presentation.cardVersionComparison"
        :class="presentation.details.length > 0 ? 'mt-4' : ''"
        :comparison="presentation.cardVersionComparison"
        @click.stop
        @open-card="openComparedCard"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import { Bell, BookOpenText, ChevronDown, ExternalLink, Flag, Layers3, RefreshCw } from 'lucide-vue-next';
import { computed, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { buildNotificationTargetLocation } from '@/domain/notifications/notificationRouteState';
import InfoTooltip from '@/shared/components/InfoTooltip.vue';
import NotificationCardVersionComparison from '@/features/notifications/components/NotificationCardVersionComparison.vue';
import type { UserNotification } from '@/domain/notifications/types';
import {
  presentNotification,
  type NotificationAction,
} from '@/features/notifications/utils/notificationPresentation';

const props = defineProps<{
  notification: UserNotification;
}>();

const emit = defineEmits<{
  interact: [notification: UserNotification];
}>();

const router = useRouter();
const detailsOpen = ref(false);
const presentation = computed(() => presentNotification(props.notification));
const hasExpandableContent = computed(() =>
  presentation.value.details.length > 0 || presentation.value.cardVersionComparison !== null,
);
const detailsId = computed(() => `notification-details-${props.notification.id}`);
const eventIcon = computed(() => {
  if (presentation.value.kind === 'flag-review') {
    return Flag;
  }
  if (presentation.value.kind === 'deck-card-update') {
    return RefreshCw;
  }
  return Bell;
});
const actionIcon = (icon: NotificationAction['icon']) => {
  if (icon === 'deck') {
    return BookOpenText;
  }
  if (icon === 'card') {
    return Layers3;
  }
  return ExternalLink;
};
const formattedDate = computed(() =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(props.notification.last_event_at)),
);

const handleRowInteraction = (): void => {
  if (hasExpandableContent.value) {
    detailsOpen.value = !detailsOpen.value;
  }
  emit('interact', props.notification);
};

const handleAction = (): void => {
  emit('interact', props.notification);
};

const openComparedCard = (versionId: string): void => {
  const comparison = presentation.value.cardVersionComparison;
  if (!comparison) {
    return;
  }
  emit('interact', props.notification);
  void router.push(buildNotificationTargetLocation(
    `/cards/${comparison.cardId}`,
    { version_id: versionId },
  ));
};
</script>

<style scoped>
.notification-row {
  border-left: 3px solid transparent;
  padding-left: 0.75rem;
  padding-right: 0.75rem;
  cursor: pointer;
  transition:
    background-color 150ms ease,
    opacity 150ms ease;
}

.notification-row:hover,
.notification-row:focus-within {
  background: color-mix(in srgb, var(--color-surface-soft) 38%, transparent);
}

.notification-details-trigger:focus-visible {
  outline: 2px solid var(--theme-accent);
  outline-offset: 2px;
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

.notification-details-chevron {
  transition: transform 150ms ease;
}

.notification-details-chevron-open {
  transform: rotate(180deg);
}
</style>

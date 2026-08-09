<template>
  <article class="theme-divider border-b last:border-b-0">
    <button
      type="button"
      class="grid min-h-20 w-full items-center gap-3 rounded-lg px-2 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-input-focus)] sm:grid-cols-[7.5rem_minmax(0,1fr)_9rem_2.5rem] sm:px-3"
      :aria-expanded="expanded"
      @click="$emit('toggle')"
    >
      <span class="flex items-center gap-2">
        <span
          class="theme-pill px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em]"
          :class="statusClass(item.status)"
        >
          {{ item.status }}
        </span>
        <AlertTriangle
          v-if="item.error_message"
          class="h-4 w-4 shrink-0 text-[var(--color-danger-text)]"
          aria-label="Has error details"
        />
      </span>

      <span class="min-w-0">
        <span class="theme-section-title block truncate text-sm font-semibold">{{
          item.title
        }}</span>
        <span class="theme-section-muted mt-1 block truncate text-xs">
          Updated {{ formatTimestamp(item.updated_at) }}
        </span>
      </span>

      <span class="theme-section-muted text-xs sm:text-right">
        <template v-if="progressPercent !== null">
          <span class="theme-section-title block font-semibold">
            {{ item.progress_current }}/{{ item.progress_total }}
          </span>
          <span class="mt-1 block">{{ progressPercent }}% complete</span>
        </template>
        <span
          v-else
          class="hidden sm:block"
        >Details</span>
      </span>

      <span class="flex justify-end">
        <ChevronDown
          class="theme-section-muted h-5 w-5 transition-transform"
          :class="expanded ? 'rotate-180' : ''"
        />
      </span>
    </button>

    <div
      v-if="expanded"
      class="px-2 pb-5 sm:px-3"
    >
      <div class="theme-card-frame-muted space-y-5 rounded-xl p-4 sm:p-5">
        <dl class="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2 xl:grid-cols-3">
          <div>
            <dt class="theme-kicker text-[11px] uppercase tracking-[0.14em]">
              Created
            </dt>
            <dd class="theme-section-muted mt-1">
              {{ formatTimestamp(item.created_at) }}
            </dd>
          </div>
          <div>
            <dt class="theme-kicker text-[11px] uppercase tracking-[0.14em]">
              Started
            </dt>
            <dd class="theme-section-muted mt-1">
              {{ formatTimestamp(item.started_at) }}
            </dd>
          </div>
          <div>
            <dt class="theme-kicker text-[11px] uppercase tracking-[0.14em]">
              Finished
            </dt>
            <dd class="theme-section-muted mt-1">
              {{ formatTimestamp(item.finished_at) }}
            </dd>
          </div>
          <div
            v-for="metadata in item.metadata"
            :key="`${item.id}-${metadata.label}`"
            class="min-w-0"
          >
            <dt class="theme-kicker text-[11px] uppercase tracking-[0.14em]">
              {{ metadata.label }}
            </dt>
            <dd class="theme-section-muted mt-1 break-all">
              {{ metadata.value }}
            </dd>
          </div>
        </dl>

        <div
          v-if="progressPercent !== null"
          class="space-y-2"
        >
          <div class="flex items-center justify-between gap-3 text-xs">
            <span class="theme-section-muted">Progress</span>
            <span class="theme-section-title font-semibold">
              {{ item.progress_current }}/{{ item.progress_total }} · {{ progressPercent }}%
            </span>
          </div>
          <div class="h-2 overflow-hidden rounded-full bg-[var(--color-surface-muted)]">
            <div
              class="h-full rounded-full bg-[var(--color-accent)] transition-all"
              :style="{ width: `${progressPercent}%` }"
            />
          </div>
        </div>

        <p
          v-if="item.error_message"
          class="theme-alert-danger whitespace-pre-wrap text-sm"
        >
          {{ item.error_message }}
        </p>

        <div
          v-if="item.links.length > 0"
          class="flex flex-wrap gap-2"
        >
          <a
            v-for="link in item.links"
            :key="link.href"
            class="btn-secondary inline-flex items-center gap-2"
            :href="operationsLinkUrl(link.href)"
          >
            {{ link.label }}
            <ExternalLink class="h-4 w-4" />
          </a>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { AlertTriangle, ChevronDown, ExternalLink } from 'lucide-vue-next';
import { computed } from 'vue';
import { operationsLinkUrl } from '@/features/operations/api';
import type { OperationsQueueItem } from '@/features/operations/types';
import {
  formatOperationsTimestamp,
  operationsProgressPercent,
  operationsStatusClass,
} from '@/features/operations/utils/operationsUtils';

const props = defineProps<{
  item: OperationsQueueItem;
  expanded: boolean;
}>();

defineEmits<{
  (event: 'toggle'): void;
}>();

const progressPercent = computed(() => operationsProgressPercent(props.item));
const statusClass = operationsStatusClass;
const formatTimestamp = formatOperationsTimestamp;
</script>

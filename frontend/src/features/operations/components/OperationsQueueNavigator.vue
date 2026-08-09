<template>
  <AppSideNav
    title="Queues"
    description="Choose a queue to inspect its worker pool and recent history."
    navigation-label="Operations queues"
    list-class="hidden gap-2 xl:grid"
  >
    <template #mobile>
      <div class="xl:hidden">
        <label class="theme-kicker mb-2 block text-[11px] font-semibold uppercase tracking-[0.14em]">
          Selected queue
        </label>
        <AppSelect
          :model-value="selectedQueueKey"
          :options="queueOptions"
          aria-label="Selected operations queue"
          @update:model-value="selectMobileQueue"
        />
        <div
          v-if="selectedQueue"
          class="theme-divider mt-3 flex flex-wrap items-center gap-2 border-t pt-3"
        >
          <span
            v-if="selectedWorker"
            class="theme-pill px-2.5 py-1 text-xs font-semibold"
            :class="workerHealthClass(selectedWorker)"
          >
            {{ workerStatusLabel(selectedWorker) }}
          </span>
          <span class="theme-section-muted text-xs">
            {{ selectedQueue.total_count }} total records
          </span>
        </div>
      </div>
    </template>

    <AppSideNavItem
      v-for="queue in queues"
      :key="queue.key"
      :label="queue.display_name"
      :description="`${queue.total_count} total records`"
      :active="queue.key === selectedQueueKey"
      @click="$emit('select', queue.key)"
    >
      <template #trailing>
        <span
          v-if="workerForQueue(queue)"
          class="mt-1 h-2.5 w-2.5 shrink-0 rounded-full ring-4 ring-[var(--color-surface-soft)]"
          :class="workerDotClass(workerForQueue(queue)!)"
          :title="workerStatusLabel(workerForQueue(queue)!)"
        />
      </template>
      <template #meta>
        <div
          v-if="statusEntries(queue).length > 0"
          class="flex flex-wrap gap-1.5"
        >
          <span
            v-for="entry in statusEntries(queue)"
            :key="entry.status"
            class="theme-pill px-2 py-0.5 text-[10px] font-semibold capitalize"
            :class="statusClass(entry.status)"
          >
            {{ entry.status }} {{ entry.count }}
          </span>
        </div>
        <p
          v-else
          class="theme-section-muted text-xs"
        >
          No activity yet
        </p>
      </template>
    </AppSideNavItem>

    <template #after>
      <p class="theme-section-muted px-1 text-xs">
        Updated {{ formatTimestamp(generatedAt) }}
      </p>
    </template>
  </AppSideNav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import AppSelect from '@/shared/components/app/AppSelect.vue';
import AppSideNav from '@/shared/components/app/AppSideNav.vue';
import AppSideNavItem from '@/shared/components/app/AppSideNavItem.vue';
import type {
  OperationsItemStatus,
  OperationsQueue,
  WorkerOverview,
} from '@/features/operations/types';
import {
  formatOperationsTimestamp,
  operationsStatusClass,
  operationsStatusEntries,
  workerHealthClass,
  workerStatusLabel,
} from '@/features/operations/utils/operationsUtils';

const props = defineProps<{
  queues: OperationsQueue[];
  workers: WorkerOverview[];
  selectedQueueKey: string | null;
  generatedAt: string;
}>();

const emit = defineEmits<{
  (event: 'select', queueKey: string): void;
}>();

const queueOptions = computed(() =>
  props.queues.map((queue) => ({ value: queue.key, label: queue.display_name })),
);
const selectedQueue = computed(
  () => props.queues.find((queue) => queue.key === props.selectedQueueKey) ?? null,
);
const selectedWorker = computed(() =>
  selectedQueue.value ? workerForQueue(selectedQueue.value) : null,
);

const workerForQueue = (queue: OperationsQueue): WorkerOverview | null =>
  props.workers.find((worker) => worker.key === queue.worker_key) ?? null;

const workerDotClass = (worker: WorkerOverview): string => {
  if (worker.health === 'online' && worker.activity === 'busy')
    return 'bg-[var(--color-warning-text)]';
  if (worker.health === 'online') return 'bg-[var(--color-success-text)]';
  if (worker.health === 'stale') return 'bg-[var(--color-danger-text)]';
  return 'bg-[var(--color-text-soft)]';
};

const selectMobileQueue = (value: string | number | null): void => {
  if (typeof value === 'string') emit('select', value);
};

const statusEntries = operationsStatusEntries;
const statusClass = (status: OperationsItemStatus): string => operationsStatusClass(status);
const formatTimestamp = formatOperationsTimestamp;
</script>

<template>
  <section class="theme-divider border-y py-4">
    <div
      v-if="worker"
      class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <h4 class="theme-section-title text-sm font-semibold">
            {{ worker.display_name }}
          </h4>
          <span
            class="theme-pill px-2.5 py-1 text-xs font-semibold"
            :class="workerHealthClass(worker)"
          >
            {{ workerStatusLabel(worker) }}
          </span>
        </div>
        <p class="theme-section-muted mt-1 text-xs">
          {{ worker.active_instances }} active instance{{
            worker.active_instances === 1 ? '' : 's'
          }}
          · Last heartbeat {{ formatTimestamp(worker.last_seen_at) }}
        </p>
      </div>
      <button
        v-if="worker.instances.length > 0"
        type="button"
        class="btn-secondary inline-flex shrink-0 items-center gap-2 px-3 py-2 text-xs"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        {{
          expanded
            ? 'Hide instances'
            : `Inspect ${worker.instances.length} instance${worker.instances.length === 1 ? '' : 's'}`
        }}
        <ChevronDown
          class="h-4 w-4 transition-transform"
          :class="expanded ? 'rotate-180' : ''"
        />
      </button>
    </div>

    <div
      v-else
      class="theme-section-muted text-sm"
    >
      No worker pool is registered for this queue.
    </div>

    <div
      v-if="worker && expanded"
      class="theme-divider mt-4 border-t"
    >
      <article
        v-for="instance in worker.instances"
        :key="instance.id"
        class="theme-divider grid gap-3 border-b py-4 last:border-b-0 last:pb-0 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)]"
      >
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="theme-section-title text-sm font-semibold">{{
              instance.display_name
            }}</span>
            <span
              class="theme-pill px-2 py-0.5 text-[10px] font-semibold"
              :class="workerHealthClass(instance)"
            >
              {{ workerStatusLabel(instance) }}
            </span>
          </div>
          <p class="theme-section-muted mt-1 break-all font-mono text-xs">
            {{ instance.id }}
          </p>
        </div>
        <dl class="text-xs">
          <dt class="theme-kicker uppercase tracking-[0.14em]">
            Current work
          </dt>
          <dd class="theme-section-muted mt-1 break-all font-mono">
            {{ instance.current_work_id ?? 'Idle' }}
          </dd>
        </dl>
        <dl class="grid gap-2 text-xs">
          <div>
            <dt class="theme-kicker uppercase tracking-[0.14em]">
              Started
            </dt>
            <dd class="theme-section-muted mt-1">
              {{ formatTimestamp(instance.started_at) }}
            </dd>
          </div>
          <div>
            <dt class="theme-kicker uppercase tracking-[0.14em]">
              Last heartbeat
            </dt>
            <dd class="theme-section-muted mt-1">
              {{ formatTimestamp(instance.last_seen_at) }}
            </dd>
          </div>
        </dl>
      </article>
    </div>
    <p class="theme-section-muted mt-3 text-xs">
      A worker is stale after {{ staleAfterSeconds }} seconds without a heartbeat.
    </p>
  </section>
</template>

<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next';
import { ref, watch } from 'vue';
import type { WorkerOverview } from '@/features/operations/types';
import {
  formatOperationsTimestamp,
  workerHealthClass,
  workerStatusLabel,
} from '@/features/operations/utils/operationsUtils';

const props = defineProps<{
  worker: WorkerOverview | null;
  staleAfterSeconds: number;
}>();

const expanded = ref(false);
watch(
  () => props.worker?.key,
  () => {
    expanded.value = false;
  },
);

const formatTimestamp = formatOperationsTimestamp;
</script>

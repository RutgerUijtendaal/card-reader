<template>
  <section data-testid="import-activity-panel">
    <div class="space-y-3">
      <div>
        <h3 class="theme-section-title text-base font-semibold">
          Import activity
        </h3>
        <p class="theme-section-muted mt-1 text-sm">
          {{ queuedCount }} queued · {{ runningCount + cancelingCount }} active
          <span v-if="lastRefreshedAt"> · Updated {{ lastRefreshedAt }}</span>
        </p>
      </div>
      <div
        class="flex flex-nowrap items-center gap-2"
        data-testid="import-activity-actions"
      >
        <button
          class="btn-secondary inline-flex shrink-0 items-center gap-2 whitespace-nowrap px-3 py-2 text-xs"
          type="button"
          :disabled="refreshing"
          aria-label="Refresh import activity"
          @click="emit('refresh')"
        >
          <RefreshCw
            class="h-3.5 w-3.5"
            :class="refreshing ? 'animate-spin' : ''"
          />
          {{ refreshing ? 'Refreshing…' : 'Refresh' }}
        </button>
        <RouterLink
          class="btn-secondary inline-flex shrink-0 items-center gap-2 whitespace-nowrap px-3 py-2 text-xs"
          to="/operations#queue-imports"
        >
          <ExternalLink class="h-3.5 w-3.5" />
          Full history
        </RouterLink>
      </div>
    </div>

    <p
      v-if="errorMessage"
      class="theme-alert-danger mt-5 text-sm"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <div
      v-if="!loaded"
      class="theme-divider mt-5 border-t"
      aria-label="Loading import activity"
    >
      <div
        v-for="index in 3"
        :key="index"
        class="theme-divider animate-pulse space-y-3 border-b py-4 last:border-b-0"
      >
        <div class="h-4 w-24 rounded bg-[var(--color-surface-muted)]" />
        <div class="h-4 w-2/3 rounded bg-[var(--color-surface-muted)]" />
        <div class="h-1.5 w-full rounded bg-[var(--color-surface-muted)]" />
      </div>
    </div>

    <div
      v-else
      class="theme-divider mt-5 border-t"
    >
      <section
        class="pt-5"
        aria-labelledby="active-imports-heading"
      >
        <div class="flex items-center gap-2">
          <Activity class="theme-section-muted h-4 w-4" />
          <h4
            id="active-imports-heading"
            class="theme-section-title text-sm font-semibold"
          >
            Active imports
          </h4>
        </div>

        <p
          v-if="activeJobs.length === 0"
          class="theme-section-muted py-4 text-sm"
        >
          No active imports.
        </p>

        <div
          v-else
          class="mt-3"
        >
          <article
            v-for="job in activeJobs"
            :key="job.id"
            class="theme-divider space-y-3 border-b py-4 first:pt-1 last:border-b-0"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0 space-y-1.5">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.14em]"
                  :class="getImportJobStatusClass(job.status)"
                >
                  {{ job.status }}
                </span>
                <p class="theme-section-title text-sm font-semibold leading-5">
                  {{ job.template_id }} · {{ job.content_version?.version_number ?? 'Unversioned' }}
                </p>
              </div>
              <span class="theme-section-muted shrink-0 text-xs">
                {{ job.processed_items }}/{{ job.total_items }}
              </span>
            </div>

            <div
              class="theme-card-frame-muted h-1.5 overflow-hidden rounded-full"
              role="progressbar"
              :aria-valuenow="getImportJobProgressPercent(job)"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div
                class="h-full rounded-full transition-all"
                :class="getImportJobProgressClass(job.status)"
                :style="{ width: `${getImportJobProgressPercent(job)}%` }"
              />
            </div>

            <div class="flex items-center justify-between gap-3">
              <span class="theme-section-muted text-xs">
                Updated {{ formatImportJobTimestamp(job.updated_at) }}
              </span>
              <button
                v-if="canCancelImportJob(job)"
                class="btn-danger-secondary shrink-0 rounded-full px-2.5 py-1 text-xs"
                type="button"
                :disabled="cancellingJobIds.has(job.id)"
                @click="emit('cancel', job.id)"
              >
                {{ cancellingJobIds.has(job.id) ? 'Interrupting…' : 'Interrupt' }}
              </button>
            </div>
          </article>
        </div>
      </section>

      <section
        class="theme-divider mt-2 border-t pt-5"
        aria-labelledby="recent-imports-heading"
      >
        <h4
          id="recent-imports-heading"
          class="theme-section-title text-sm font-semibold"
        >
          Recently finished
        </h4>
        <p class="theme-section-muted mt-1 text-xs">
          Latest completed, failed, or cancelled work.
        </p>

        <p
          v-if="recentJobs.length === 0"
          class="theme-section-muted py-4 text-sm"
        >
          No recent import history.
        </p>

        <div
          v-else
          class="mt-3"
        >
          <article
            v-for="job in recentJobs"
            :key="job.id"
            class="theme-divider space-y-2.5 border-b py-4 first:pt-1 last:border-b-0"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0 space-y-1.5">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.14em]"
                  :class="getImportJobStatusClass(job.status)"
                >
                  {{ job.status }}
                </span>
                <p class="theme-section-title text-sm font-semibold leading-5">
                  {{ job.title }}
                </p>
              </div>
              <span
                v-if="job.progress_current !== null && job.progress_total !== null"
                class="theme-section-muted shrink-0 text-xs"
              >
                {{ job.progress_current }}/{{ job.progress_total }}
              </span>
            </div>

            <div
              v-if="getOperationsItemProgressPercent(job) !== null"
              class="theme-card-frame-muted h-1.5 overflow-hidden rounded-full"
              role="progressbar"
              :aria-valuenow="getOperationsItemProgressPercent(job) ?? undefined"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div
                class="h-full rounded-full"
                :class="getImportJobProgressClass(job.status)"
                :style="{ width: `${getOperationsItemProgressPercent(job)}%` }"
              />
            </div>

            <span class="theme-section-muted block text-xs">
              Updated {{ formatImportJobTimestamp(job.updated_at) }}
            </span>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Activity, ExternalLink, RefreshCw } from 'lucide-vue-next';
import { RouterLink } from 'vue-router';
import type { OperationsQueueItem } from '@/domain/operations/types';
import type { ImportJob } from '@/features/import-jobs/types';
import {
  canCancelImportJob,
  formatImportJobTimestamp,
  getImportJobProgressClass,
  getImportJobProgressPercent,
  getImportJobStatusClass,
  getOperationsItemProgressPercent,
} from '@/features/import-jobs/utils/importJobUtils';

defineProps<{
  activeJobs: ImportJob[];
  recentJobs: OperationsQueueItem[];
  loaded: boolean;
  refreshing: boolean;
  errorMessage: string;
  queuedCount: number;
  runningCount: number;
  cancelingCount: number;
  cancellingJobIds: Set<string>;
  lastRefreshedAt: string | null;
}>();

const emit = defineEmits<{
  refresh: [];
  cancel: [jobId: string];
}>();
</script>

<template>
  <section class="flex flex-col gap-8">
    <AppPageHeader
      :icon="ServerCog"
      title="Operations"
      subtitle="Monitor background workers and the durable queues they process."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          :disabled="refreshing"
          @click="loadOverview"
        >
          <RefreshCw
            class="h-4 w-4"
            :class="refreshing ? 'animate-spin' : ''"
          />
          {{ refreshing ? 'Refreshing…' : 'Refresh' }}
        </button>
      </template>
    </AppPageHeader>

    <AppPageLayout
      columns="one"
      main-class="space-y-8"
    >
      <div
        v-if="loading && !overview"
        class="space-y-8"
      >
        <div class="grid gap-4 md:grid-cols-3">
          <div
            v-for="index in 3"
            :key="`worker-skeleton-${index}`"
            class="theme-card-frame-muted space-y-4 rounded-xl border p-5"
          >
            <div class="h-5 w-1/2 animate-pulse rounded bg-[var(--color-surface-muted)]" />
            <div class="h-7 w-28 animate-pulse rounded-full bg-[var(--color-surface-muted)]" />
            <div class="h-4 w-3/4 animate-pulse rounded bg-[var(--color-surface-muted)]" />
          </div>
        </div>
        <div class="grid items-start gap-5 lg:grid-cols-3">
          <div
            v-for="index in 3"
            :key="`queue-skeleton-${index}`"
            class="theme-card-frame-muted space-y-4 rounded-2xl border p-5 sm:p-6"
          >
            <div class="h-6 w-48 animate-pulse rounded bg-[var(--color-surface-muted)]" />
            <div class="h-24 w-full animate-pulse rounded-xl bg-[var(--color-surface-muted)]" />
          </div>
        </div>
      </div>

      <div
        v-else-if="errorMessage && !overview"
        class="theme-alert-danger"
        role="alert"
      >
        <p>{{ errorMessage }}</p>
        <button
          class="btn-secondary mt-3"
          type="button"
          @click="loadOverview"
        >
          Try again
        </button>
      </div>

      <template v-else-if="overview">
        <section>
          <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h3 class="theme-section-title text-lg font-semibold">
                Workers
              </h3>
              <p class="theme-section-muted mt-1 text-sm">
                A worker is stale after {{ overview.stale_after_seconds }} seconds without a
                heartbeat.
              </p>
            </div>
            <p class="theme-section-muted text-sm">
              Updated {{ formatTimestamp(overview.generated_at) }}
            </p>
          </div>

          <div class="grid gap-4 md:grid-cols-3">
            <article
              v-for="worker in overview.workers"
              :key="worker.key"
              class="theme-card-frame-muted rounded-xl border p-5"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <h4 class="theme-section-title font-semibold">
                    {{ worker.display_name }}
                  </h4>
                  <p class="theme-section-muted mt-1 text-xs">
                    {{ worker.active_instances }} active instance{{
                      worker.active_instances === 1 ? '' : 's'
                    }}
                  </p>
                </div>
                <span
                  class="theme-pill shrink-0 px-2.5 py-1 text-xs font-semibold"
                  :class="healthClass(worker)"
                >
                  {{ workerStatusLabel(worker) }}
                </span>
              </div>
              <dl class="theme-section-muted mt-5 space-y-3 text-sm">
                <div>
                  <dt class="theme-kicker text-[11px] uppercase tracking-[0.16em]">
                    Last heartbeat
                  </dt>
                  <dd class="theme-section-title mt-1">
                    {{ formatTimestamp(worker.last_seen_at) }}
                  </dd>
                </div>
                <div v-if="worker.current_work_ids.length > 0">
                  <dt class="theme-kicker text-[11px] uppercase tracking-[0.16em]">
                    Current work
                  </dt>
                  <dd class="theme-section-title mt-1 truncate font-mono text-xs">
                    {{ worker.current_work_ids.join(', ') }}
                  </dd>
                </div>
              </dl>
            </article>
          </div>
        </section>

        <p
          v-if="errorMessage"
          class="theme-alert-warning"
          role="status"
        >
          {{ errorMessage }} Showing the last successful update.
        </p>

        <section>
          <div>
            <h3 class="theme-section-title text-lg font-semibold">
              Queues
            </h3>
            <p class="theme-section-muted mt-1 text-sm">
              Recent work grouped by the worker responsible for processing it.
            </p>
          </div>

          <div class="mt-5 grid items-start gap-5 lg:grid-cols-3">
            <article
              v-for="queue in overview.queues"
              :id="`queue-${queue.key}`"
              :key="queue.key"
              class="theme-card-frame-muted scroll-mt-24 rounded-2xl border p-5 sm:p-6"
            >
              <div class="flex flex-wrap items-start justify-between gap-4">
                <div class="min-w-0">
                  <h4 class="theme-section-title text-base font-semibold">
                    {{ queue.display_name }}
                  </h4>
                  <p class="theme-section-muted mt-1 text-sm">
                    {{ queue.total_count }} total records
                  </p>
                </div>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="entry in statusEntries(queue)"
                    :key="entry.status"
                    class="theme-pill px-2.5 py-1 text-xs font-semibold capitalize"
                    :class="statusClass(entry.status)"
                  >
                    {{ entry.status }} {{ entry.count }}
                  </span>
                </div>
              </div>

              <div
                v-if="queue.items.length === 0"
                class="theme-section-muted mt-5 rounded-xl border border-dashed px-4 py-8 text-center text-sm"
              >
                No queue activity yet.
              </div>

              <div
                v-else
                class="theme-divider mt-5 border-t"
              >
                <article
                  v-for="item in queue.items"
                  :key="item.id"
                  class="theme-divider border-b py-5 last:border-b-0 last:pb-0"
                >
                  <div class="min-w-0 space-y-4">
                    <div class="space-y-2">
                      <div class="flex flex-wrap items-center gap-2">
                        <span
                          class="theme-pill px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.12em]"
                          :class="statusClass(item.status)"
                        >
                          {{ item.status }}
                        </span>
                        <h5 class="theme-section-title min-w-0 break-words text-sm font-semibold">
                          {{ item.title }}
                        </h5>
                      </div>
                      <p class="theme-section-muted text-xs">
                        Updated {{ formatTimestamp(item.updated_at) }}
                      </p>
                    </div>

                    <dl
                      class="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-1 2xl:grid-cols-2"
                    >
                      <div
                        v-for="metadata in item.metadata"
                        :key="`${item.id}-${metadata.label}`"
                        class="min-w-0"
                      >
                        <dt class="theme-kicker text-[11px] uppercase tracking-[0.14em]">
                          {{ metadata.label }}
                        </dt>
                        <dd class="theme-section-muted mt-0.5 break-all">
                          {{ metadata.value }}
                        </dd>
                      </div>
                    </dl>

                    <p
                      v-if="item.error_message"
                      class="theme-alert-danger text-sm"
                    >
                      {{ item.error_message }}
                    </p>

                    <div
                      v-if="progressPercent(item) !== null"
                      class="flex items-center gap-3"
                    >
                      <span class="theme-section-muted shrink-0 text-sm">
                        {{ item.progress_current }}/{{ item.progress_total }}
                      </span>
                      <div class="theme-card-frame-muted h-2 flex-1 rounded-full">
                        <div
                          class="h-full rounded-full bg-[var(--color-accent)] transition-all"
                          :style="{ width: `${progressPercent(item)}%` }"
                        />
                      </div>
                    </div>

                    <div
                      v-if="item.links.length > 0"
                      class="flex flex-wrap gap-2"
                    >
                      <a
                        v-for="link in item.links"
                        :key="link.href"
                        class="btn-secondary"
                        :href="operationsLinkUrl(link.href)"
                      >
                        {{ link.label }}
                      </a>
                    </div>
                  </div>
                </article>
              </div>
            </article>
          </div>
        </section>
      </template>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { RefreshCw, ServerCog } from 'lucide-vue-next';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import { operationsLinkUrl } from '@/features/operations/api';
import { useOperationsOverview } from '@/features/operations/composables/useOperationsOverview';
import type { OperationsItemStatus } from '@/features/operations/types';
import {
  formatOperationsTimestamp,
  operationsProgressPercent,
  operationsStatusClass,
  operationsStatusEntries,
  workerHealthClass,
  workerStatusLabel,
} from '@/features/operations/utils/operationsUtils';

const { overview, loading, refreshing, errorMessage, loadOverview } = useOperationsOverview();
const formatTimestamp = formatOperationsTimestamp;
const statusEntries = operationsStatusEntries;
const healthClass = workerHealthClass;
const progressPercent = operationsProgressPercent;
const statusClass = (status: OperationsItemStatus): string => operationsStatusClass(status);
</script>

<template>
  <section class="flex flex-col gap-5">
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
          :disabled="refreshing || historyRefreshing"
          @click="refreshWorkspace"
        >
          <RefreshCw
            class="h-4 w-4"
            :class="refreshing || historyRefreshing ? 'animate-spin' : ''"
          />
          {{ refreshing || historyRefreshing ? 'Refreshing…' : 'Refresh' }}
        </button>
      </template>
    </AppPageHeader>

    <AppPageLayout
      columns="one"
      root-class="app-page-layout-standard"
    >
      <template #aside>
        <AppStickyAside>
          <OperationsQueueNavigator
            v-if="overview"
            :queues="overview.queues"
            :workers="overview.workers"
            :selected-queue-key="selectedQueueKey"
            :generated-at="overview.generated_at"
            @select="selectQueue"
          />
          <div
            v-else-if="loading"
            class="space-y-3"
          >
            <div class="h-5 w-24 animate-pulse rounded bg-[var(--color-surface-muted)]" />
            <div class="h-4 w-full animate-pulse rounded bg-[var(--color-surface-muted)]" />
            <div
              v-for="index in 3"
              :key="`queue-navigation-loading-${index}`"
              class="h-24 animate-pulse rounded-xl bg-[var(--color-surface-muted)]"
            />
          </div>
        </AppStickyAside>
      </template>

      <div
        v-if="loading && !overview"
        class="space-y-6"
      >
        <section class="space-y-4">
          <div class="h-7 w-56 animate-pulse rounded bg-[var(--color-surface-muted)]" />
          <div class="h-4 w-72 animate-pulse rounded bg-[var(--color-surface-muted)]" />
          <div class="h-20 animate-pulse rounded-xl bg-[var(--color-surface-muted)]" />
        </section>
        <section class="theme-divider border-t pt-5">
          <div class="h-6 w-40 animate-pulse rounded bg-[var(--color-surface-muted)]" />
          <div class="mt-4 divide-y divide-[var(--color-border)]">
            <div
              v-for="index in 6"
              :key="`queue-history-loading-${index}`"
              class="h-20 animate-pulse bg-[var(--color-surface-soft)]"
            />
          </div>
        </section>
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

      <div
        v-else-if="overview && selectedQueue"
        :id="`queue-${selectedQueue.key}`"
        class="scroll-mt-24 space-y-6"
      >
        <p
          v-if="errorMessage"
          class="theme-alert-warning"
          role="status"
        >
          {{ errorMessage }} Showing the last successful worker and queue summary.
        </p>

        <section>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0">
              <p class="theme-kicker text-[11px] font-semibold uppercase tracking-[0.16em]">
                Selected queue
              </p>
              <h3 class="theme-section-title mt-1 text-xl font-semibold">
                {{ selectedQueue.display_name }}
              </h3>
              <p class="theme-section-muted mt-1 text-sm">
                {{ selectedQueue.total_count }} total records · Recent work ordered by last update
              </p>
            </div>
            <div class="flex max-w-2xl flex-wrap gap-2 sm:justify-end">
              <span
                v-for="entry in statusEntries(selectedQueue)"
                :key="entry.status"
                class="theme-pill px-2.5 py-1 text-xs font-semibold capitalize"
                :class="statusClass(entry.status)"
              >
                {{ entry.status }} {{ entry.count }}
              </span>
            </div>
          </div>

          <OperationsWorkerPool
            class="mt-5"
            :worker="selectedWorker"
            :stale-after-seconds="overview.stale_after_seconds"
          />
        </section>

        <section>
          <div
            class="theme-divider flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-end sm:justify-between"
          >
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <h4 class="theme-section-title text-base font-semibold">
                  Recent work
                </h4>
                <RefreshCw
                  v-if="historyRefreshing"
                  class="theme-section-muted h-3.5 w-3.5 animate-spin"
                  aria-label="Refreshing queue history"
                />
              </div>
              <p class="theme-section-muted mt-1 text-sm">
                <template v-if="historyPage">
                  {{ historyPage.count }} records · Page {{ historyPage.page }} of {{ totalPages }}
                </template>
                <template v-else>
                  Queue history
                </template>
              </p>
            </div>
            <button
              v-if="pageNumber > 1"
              type="button"
              class="btn-secondary px-3 py-2 text-xs"
              @click="goToPage(1)"
            >
              Back to latest
            </button>
            <p
              v-else
              class="theme-section-muted text-xs"
            >
              Latest history refreshes automatically
            </p>
          </div>

          <div
            v-if="historyErrorMessage"
            class="theme-alert-danger mt-4"
            role="alert"
          >
            <p>{{ historyErrorMessage }}</p>
            <button
              class="btn-secondary mt-3"
              type="button"
              @click="loadHistory()"
            >
              Retry history
            </button>
          </div>

          <div
            v-if="historyLoading"
            class="theme-divider divide-y"
          >
            <div
              v-for="index in 6"
              :key="`selected-queue-loading-${index}`"
              class="grid min-h-20 animate-pulse items-center gap-3 px-3 py-3 sm:grid-cols-[7.5rem_minmax(0,1fr)_9rem_2.5rem]"
            >
              <div class="h-6 w-24 rounded-full bg-[var(--color-surface-muted)]" />
              <div class="space-y-2">
                <div class="h-4 w-2/5 rounded bg-[var(--color-surface-muted)]" />
                <div class="h-3 w-48 rounded bg-[var(--color-surface-muted)]" />
              </div>
              <div class="h-4 w-20 rounded bg-[var(--color-surface-muted)]" />
              <div class="h-5 w-5 rounded bg-[var(--color-surface-muted)]" />
            </div>
          </div>

          <div
            v-else-if="historyItems.length === 0 && !historyErrorMessage"
            class="theme-section-muted flex min-h-48 items-center justify-center py-10 text-center text-sm"
          >
            <div class="space-y-1">
              <h5 class="theme-section-title text-sm font-semibold">
                No queue activity yet
              </h5>
              <p>New work will appear here when this queue receives it.</p>
            </div>
          </div>

          <div
            v-else-if="historyItems.length > 0"
            class="theme-divider"
          >
            <OperationsQueueItemRow
              v-for="item in historyItems"
              :key="item.id"
              :item="item"
              :expanded="expandedItemIds.has(item.id)"
              @toggle="toggleItem(item.id)"
            />
          </div>

          <nav
            v-if="historyPage && totalPages > 1"
            class="theme-divider mt-4 flex items-center justify-between gap-3 border-t pt-4"
            aria-label="Queue history pages"
          >
            <button
              type="button"
              class="btn-secondary px-3 py-2 text-xs"
              :disabled="historyPage.previous_page === null"
              @click="goToPage(historyPage.previous_page ?? 1)"
            >
              Previous
            </button>
            <span class="theme-section-muted text-xs">
              Page {{ historyPage.page }} of {{ totalPages }}
            </span>
            <button
              type="button"
              class="btn-secondary px-3 py-2 text-xs"
              :disabled="historyPage.next_page === null"
              @click="goToPage(historyPage.next_page ?? historyPage.page)"
            >
              Next
            </button>
          </nav>
        </section>
      </div>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { RefreshCw, ServerCog } from 'lucide-vue-next';
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
import OperationsQueueItemRow from '@/features/operations/components/OperationsQueueItemRow.vue';
import OperationsQueueNavigator from '@/features/operations/components/OperationsQueueNavigator.vue';
import OperationsWorkerPool from '@/features/operations/components/OperationsWorkerPool.vue';
import { useOperationsOverview } from '@/features/operations/composables/useOperationsOverview';
import { useOperationsQueueHistory } from '@/features/operations/composables/useOperationsQueueHistory';
import type { OperationsItemStatus } from '@/domain/operations/types';
import {
  defaultOperationsQueueKey,
  operationsPageCount,
  operationsStatusClass,
  operationsStatusEntries,
  parseOperationsPage,
} from '@/features/operations/utils/operationsUtils';

const route = useRoute();
const router = useRouter();
const { overview, loading, refreshing, errorMessage, loadOverview } = useOperationsOverview();

const requestedQueueKey = computed(() => {
  const prefix = '#queue-';
  return route.hash.startsWith(prefix) ? route.hash.slice(prefix.length) : null;
});
const selectedQueueKey = computed(() => {
  const queues = overview.value?.queues ?? [];
  const requested = requestedQueueKey.value;
  if (requested && queues.some((queue) => queue.key === requested)) return requested;
  return defaultOperationsQueueKey(queues);
});
const selectedQueue = computed(
  () => overview.value?.queues.find((queue) => queue.key === selectedQueueKey.value) ?? null,
);
const selectedWorker = computed(
  () =>
    overview.value?.workers.find((worker) => worker.key === selectedQueue.value?.worker_key) ??
    null,
);
const pageNumber = computed(() => parseOperationsPage(route.query.page));

const {
  page: historyPage,
  items: historyItems,
  loading: historyLoading,
  refreshing: historyRefreshing,
  errorMessage: historyErrorMessage,
  loadHistory,
} = useOperationsQueueHistory(selectedQueueKey, pageNumber);

const expandedItemIds = ref(new Set<string>());
const totalPages = computed(() =>
  historyPage.value ? operationsPageCount(historyPage.value.count, historyPage.value.page_size) : 1,
);

watch(
  selectedQueueKey,
  (queueKey) => {
    if (!queueKey || route.hash === `#queue-${queueKey}`) return;
    void router.replace({
      hash: `#queue-${queueKey}`,
      query: route.query,
    });
  },
  { immediate: true },
);

watch([selectedQueueKey, pageNumber], () => {
  expandedItemIds.value = new Set();
});

watch(historyItems, (items) => {
  const visibleIds = new Set(items.map((item) => item.id));
  expandedItemIds.value = new Set(
    [...expandedItemIds.value].filter((itemId) => visibleIds.has(itemId)),
  );
});

const selectQueue = (queueKey: string): void => {
  if (queueKey === selectedQueueKey.value) return;
  const query = { ...route.query };
  delete query.page;
  void router.replace({ query, hash: `#queue-${queueKey}` });
};

const goToPage = (page: number): void => {
  if (page < 1 || page === pageNumber.value) return;
  void router.push({
    hash: route.hash,
    query: {
      ...route.query,
      page: page === 1 ? undefined : String(page),
    },
  });
};

const toggleItem = (itemId: string): void => {
  const nextIds = new Set(expandedItemIds.value);
  if (nextIds.has(itemId)) nextIds.delete(itemId);
  else nextIds.add(itemId);
  expandedItemIds.value = nextIds;
};

const refreshWorkspace = async (): Promise<void> => {
  await Promise.all([loadOverview(), loadHistory({ preserve: true })]);
};

const statusEntries = operationsStatusEntries;
const statusClass = (status: OperationsItemStatus): string => operationsStatusClass(status);
</script>

<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="ClipboardCheck"
      title="Review Queue"
      subtitle="Review low-confidence parses and user-reported parse issues."
      title-tag="h2"
      title-class="text-xl"
    />

    <AppPageLayout
      columns="one"
      root-class="app-page-layout-standard"
    >
      <template #aside>
        <AppStickyAside>
          <AppSideNav
            title="Queue Views"
            description="Choose the review work to show."
            navigation-label="Review queue views"
          >
            <AppSideNavItem
              label="Flagged Parses"
              description="User-submitted parse reports."
              :active="activeView === 'flags'"
              @click="setActiveView('flags')"
            />

            <AppSideNavItem
              label="Low Confidence"
              description="Parser results below the confidence threshold."
              :active="activeView === 'confidence'"
              @click="setActiveView('confidence')"
            />

            <template #after>
              <div
                v-if="activeView === 'flags'"
                class="theme-divider space-y-2 border-t pt-4"
              >
                <p class="theme-kicker text-xs font-semibold uppercase tracking-[0.16em]">
                  Report Status
                </p>
                <div class="grid gap-2">
                  <button
                    v-for="status in flagStatuses"
                    :key="status.value"
                    class="rounded-lg border px-3 py-2 text-left text-sm font-semibold transition"
                    :class="flagStatus === status.value
                      ? 'theme-selected-surface'
                      : 'theme-card-frame theme-section-title hover:border-[var(--theme-border-strong)]'"
                    type="button"
                    @click="setFlagStatus(status.value)"
                  >
                    {{ status.label }}
                  </button>
                </div>
              </div>
            </template>
          </AppSideNav>
        </AppStickyAside>
      </template>

      <section class="pt-0">
        <div
          v-if="activeView === 'confidence'"
          class="space-y-4"
        >
          <div class="theme-divider flex flex-wrap items-center justify-between gap-3 border-b pb-4">
            <div>
              <h3 class="theme-section-title text-base font-semibold">
                Low Confidence
              </h3>
              <p class="theme-section-muted mt-1 text-sm">
                {{ cards.length }} loaded
              </p>
            </div>
            <button
              v-if="nextPage !== null"
              class="btn-secondary"
              type="button"
              @click="loadMore"
            >
              Load more
            </button>
          </div>

          <ul
            v-if="isLoadingInitial"
            class="theme-divider"
            aria-label="Loading low-confidence cards"
          >
            <li
              v-for="index in 6"
              :key="`confidence-loading-${index}`"
              class="review-list-row theme-divider py-3"
            >
              <div class="flex items-center gap-3">
                <div class="h-4 w-48 max-w-[60%] animate-pulse rounded bg-[var(--color-surface-muted)]" />
                <div class="h-4 w-14 animate-pulse rounded bg-[var(--color-surface-muted)]" />
              </div>
            </li>
          </ul>

          <div
            v-else-if="cards.length === 0"
            class="theme-section-muted flex min-h-72 items-center justify-center py-10 text-center text-sm"
          >
            <div class="space-y-1">
              <h3 class="theme-section-title text-sm font-semibold">
                No low-confidence cards
              </h3>
              <p class="mx-auto max-w-md leading-6">
                Parser confidence is clear for the current queue.
              </p>
            </div>
          </div>

          <ul
            v-else
            class="theme-divider"
          >
            <li
              v-for="card in cards"
              :key="card.id"
              class="review-list-row theme-divider py-3"
            >
              <RouterLink
                class="theme-link font-medium"
                :to="`/cards/${card.id}/edit`"
              >
                {{ card.name }}
              </RouterLink>
              <span class="theme-section-muted"> - {{ card.confidence }}</span>
            </li>
          </ul>
        </div>

        <div
          v-else
          class="space-y-4"
        >
          <div class="theme-divider flex flex-wrap items-start justify-between gap-3 border-b pb-4">
            <div>
              <h3 class="theme-section-title text-base font-semibold">
                Flagged Parses
              </h3>
              <p class="theme-section-muted mt-1 text-sm">
                {{ flagGroups.length }} loaded · {{ flagPage?.count ?? 0 }} reports
              </p>
            </div>
          </div>

          <ul
            v-if="loadingFlags"
            class="theme-divider"
            aria-label="Loading flagged parse reports"
          >
            <li
              v-for="index in 3"
              :key="`flag-loading-${index}`"
              class="review-report-row theme-divider grid gap-4 py-5 sm:grid-cols-[10rem_minmax(0,1fr)] lg:grid-cols-[12rem_minmax(0,1fr)]"
            >
              <div class="mx-auto block aspect-[3/4] w-44 max-w-full animate-pulse rounded-lg bg-[var(--color-surface-muted)] sm:mx-0 sm:w-full" />

              <div class="min-w-0 space-y-4">
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div class="min-w-0 space-y-2">
                    <div class="h-5 w-48 max-w-full animate-pulse rounded bg-[var(--color-surface-muted)]" />
                    <div class="h-3 w-72 max-w-full animate-pulse rounded bg-[var(--color-surface-muted)]" />
                  </div>
                  <div class="h-6 w-20 animate-pulse rounded-full bg-[var(--color-surface-muted)]" />
                </div>

                <div class="grid gap-3 sm:grid-cols-3">
                  <div class="h-16 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
                  <div class="h-16 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
                  <div class="h-16 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
                </div>

                <div class="space-y-2">
                  <div class="h-4 w-full animate-pulse rounded bg-[var(--color-surface-muted)]" />
                  <div class="h-4 w-3/4 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                </div>
              </div>
            </li>
          </ul>
          <div
            v-else-if="flagGroups.length === 0"
            class="theme-section-muted flex min-h-72 items-center justify-center py-10 text-center text-sm"
          >
            <div class="space-y-1">
              <h3 class="theme-section-title text-sm font-semibold">
                No flagged reports
              </h3>
              <p class="mx-auto max-w-md leading-6">
                There are no user-submitted parse reports in this view.
              </p>
            </div>
          </div>
          <ul
            v-else
            class="theme-divider"
          >
            <li
              v-for="group in flagGroups"
              :key="group.flagId"
              class="review-report-row theme-divider grid gap-4 py-5 sm:grid-cols-[10rem_minmax(0,1fr)] lg:grid-cols-[12rem_minmax(0,1fr)]"
            >
              <RouterLink
                :to="editorLocation(group.primary, group)"
                class="mx-auto block w-44 max-w-full overflow-hidden rounded-lg sm:mx-0 sm:w-full"
              >
                <img
                  v-if="group.card.image_url"
                  :src="toAbsoluteApiUrl(group.card.image_url)"
                  :alt="group.card.name"
                  class="aspect-[3/4] w-full object-cover"
                >
                <div
                  v-else
                  class="theme-empty-state aspect-[3/4]"
                >
                  No image
                </div>
              </RouterLink>

              <div class="flex h-full min-w-0 flex-col">
                <div>
                  <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0">
                      <RouterLink
                        class="theme-link text-base font-semibold"
                        :to="editorLocation(group.primary, group)"
                      >
                        {{ group.card.name }}
                      </RouterLink>
                      <p class="theme-section-muted mt-1 text-xs">
                        {{ versionLabel(group) }} · reported by {{ group.submitted_by.username }} on {{ formatDate(group.created_at) }}
                      </p>
                    </div>
                    <span
                      class="theme-pill px-2.5 py-1 text-xs"
                      :class="groupStatusClass(group)"
                    >
                      {{ groupStatusLabel(group) }}
                    </span>
                  </div>

                  <p
                    v-if="group.note"
                    class="theme-section-muted mt-3 whitespace-pre-wrap text-sm"
                  >
                    {{ group.note }}
                  </p>

                  <div class="mt-4 grid gap-3">
                    <div
                      v-for="item in group.items"
                      :key="item.id"
                      class="theme-divider border-t pt-3"
                    >
                      <div class="flex flex-wrap items-start justify-between gap-2">
                        <div class="min-w-0">
                          <p class="theme-section-title text-sm font-semibold">
                            {{ propertyLabel(item.property_key) }}
                          </p>
                          <p
                            v-if="item.note"
                            class="theme-section-muted mt-1 whitespace-pre-wrap text-sm"
                          >
                            {{ item.note }}
                          </p>
                        </div>
                        <span
                          class="theme-pill px-2 py-0.5 text-xs"
                          :class="statusClass(item.status)"
                        >
                          {{ item.status }}
                        </span>
                      </div>

                      <div
                        v-if="item.property_key !== 'overall'"
                        class="mt-3 grid gap-3 md:grid-cols-2"
                      >
                        <div>
                          <p class="theme-kicker text-[11px] font-medium uppercase tracking-wide">
                            Reported Value
                          </p>
                          <p class="theme-section-title mt-1 whitespace-pre-wrap text-sm">
                            {{ item.captured_current_value || 'Empty' }}
                          </p>
                        </div>
                        <div>
                          <p class="theme-kicker text-[11px] font-medium uppercase tracking-wide">
                            Expected Value
                          </p>
                          <p class="theme-section-title mt-1 whitespace-pre-wrap text-sm">
                            {{ item.expected_value || 'Not provided' }}
                          </p>
                        </div>
                      </div>

                      <p
                        v-if="item.status !== 'open' && item.review_note"
                        class="theme-section-muted mt-3 text-xs"
                      >
                        Review note: {{ item.review_note }}
                      </p>
                    </div>
                  </div>
                </div>

                <div
                  v-if="openItems(group).length > 0"
                  class="theme-divider mt-auto flex flex-wrap items-center justify-end gap-2 border-t pt-3"
                >
                  <template
                    v-for="item in openItems(group)"
                    :key="`actions-${item.id}`"
                  >
                    <RouterLink
                      class="btn-primary"
                      :to="editorLocation(item, group)"
                    >
                      Open Editor
                    </RouterLink>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="updatingItemId === item.id"
                      @click="updateFlagItem(item.id, 'dismissed')"
                    >
                      Dismiss
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="updatingItemId === item.id"
                      @click="updateFlagItem(item.id, 'resolved')"
                    >
                      Resolve
                    </button>
                  </template>
                </div>
              </div>
            </li>
          </ul>

          <div
            v-if="flagPage?.next_page"
            class="flex justify-end"
          >
            <button
              class="btn-secondary"
              type="button"
              :disabled="loadingFlags"
              @click="loadFlagPage(flagPage.next_page, 'append')"
            >
              Load more
            </button>
          </div>
        </div>
      </section>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { ClipboardCheck } from 'lucide-vue-next';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { getApiErrorMessage as extractErrorMessage } from '@/shared/api/errors';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppSideNav from '@/shared/components/app/AppSideNav.vue';
import AppSideNavItem from '@/shared/components/app/AppSideNavItem.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
import { buildReviewCardEditorLocation } from '@/domain/card-navigation/cardReturnState';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import { useCardCollection } from '@/domain/cards/composables/useCardCollection';
import { useReviewSummary } from '@/domain/review/composables/useReviewSummary';
import { parseFlagPropertyLabels, type ParseFlagPropertyKey } from '@/domain/review/types';
import { queryString } from '@/shared/router/routeState';
import { fetchParseFlagPage, updateParseFlagItem } from '@/features/review-queue/api';
import type {
  FlagStatus,
  ParseFlagPage,
  ParseFlagReviewGroup,
  ParseFlagReviewItem,
  ParseFlagReviewReport,
  ReviewCard,
  ReviewView,
} from '@/features/review-queue/types';

const route = useRoute();
const router = useRouter();
const workspace = useCardPoolWorkspaceStore();
const activeView = ref<ReviewView>(queryString(route.query.view) === 'confidence' ? 'confidence' : 'flags');
const flagStatus = ref<FlagStatus>(normalizeFlagStatus(queryString(route.query.status)));
const flagReports = ref<ParseFlagReviewReport[]>([]);
const flagPage = ref<ParseFlagPage | null>(null);
const loadingFlags = ref(false);
let flagRequestGeneration = 0;
const updatingItemId = ref<string | null>(null);
const filtersLoaded = ref(true);
const { decrementOpenParseFlagItemCount, loadReviewSummary } = useReviewSummary();

const collection = useCardCollection<ReviewCard>({
  buildSearchParams: () => {
    const params = new URLSearchParams();
    params.set('max_confidence', '0.8');
    params.set('card_pool', workspace.activePool);
    return params;
  },
  filtersLoaded,
  pageSize: 100,
  resultSetKey: computed(() => workspace.generation),
});
const cards = collection.cards;
const isLoadingInitial = collection.isLoadingInitial;
const nextPage = collection.nextPage;
const flagStatuses: Array<{ value: FlagStatus; label: string }> = [
  { value: 'open', label: 'Open' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: 'all', label: 'All' },
];

const flagGroups = computed<ParseFlagReviewGroup[]>(() => {
  return flagReports.value
    .flatMap((report): ParseFlagReviewGroup[] => {
      const sortedItems = [...report.items].sort((first, second) => {
        const createdAtOrder = first.created_at.localeCompare(second.created_at);
        return createdAtOrder !== 0
          ? createdAtOrder
          : propertyLabel(first.property_key).localeCompare(propertyLabel(second.property_key));
      });
      const primary = sortedItems[0];
      if (!primary) return [];
      return [{
        ...report,
        flagId: report.id,
        items: sortedItems,
        primary,
        openCount: sortedItems.filter((item) => item.status === 'open').length,
        resolvedCount: sortedItems.filter((item) => item.status === 'resolved').length,
        dismissedCount: sortedItems.filter((item) => item.status === 'dismissed').length,
      }];
    })
    .sort((first, second) => second.created_at.localeCompare(first.created_at));
});

const loadMore = async (): Promise<void> => {
  await collection.loadNextPage();
};

const setActiveView = (view: ReviewView): void => {
  activeView.value = view;
  syncQuery();
};

const setFlagStatus = (status: FlagStatus): void => {
  flagStatus.value = status;
  syncQuery();
  void loadFlagPage(1, 'replace');
};

const syncQuery = (): void => {
  void router.replace({
    path: '/review',
    query: {
      view: activeView.value,
      status: flagStatus.value,
    },
  });
};

const loadFlagPage = async (page: number, mode: 'replace' | 'append'): Promise<void> => {
  const requestGeneration = ++flagRequestGeneration;
  const workspaceGeneration = workspace.generation;
  const cardPool = workspace.activePool;
  const status = flagStatus.value;
  loadingFlags.value = true;
  try {
    const response = await fetchParseFlagPage(status, cardPool, page, 25);
    if (
      requestGeneration !== flagRequestGeneration
      || workspaceGeneration !== workspace.generation
      || cardPool !== workspace.activePool
      || status !== flagStatus.value
    ) {
      return;
    }
    flagPage.value = response;
    flagReports.value = mode === 'append'
      ? [...flagReports.value, ...response.results]
      : response.results;
    if (flagStatus.value === 'open') {
      void loadReviewSummary();
    }
  } finally {
    if (requestGeneration === flagRequestGeneration) {
      loadingFlags.value = false;
    }
  }
};

const updateFlagItem = async (itemId: string, status: 'resolved' | 'dismissed'): Promise<void> => {
  const previousReport = flagReports.value.find((report) => report.items.some((item) => item.id === itemId));
  const previousItem = previousReport?.items.find((item) => item.id === itemId);
  const removingLastOpenItemInReport =
    flagStatus.value === 'open' &&
    previousReport?.items.filter((item) => item.status === 'open').length === 1;
  updatingItemId.value = itemId;
  try {
    const response = await updateParseFlagItem(itemId, status);
    flagReports.value = flagReports.value.map((report) => ({
      ...report,
      items: report.items.map((item) => (item.id === itemId ? response : item)),
    }));
    if (previousItem?.status === 'open') {
      decrementOpenParseFlagItemCount();
    }
    if (flagStatus.value === 'open') {
      flagReports.value = flagReports.value
        .map((report) => ({
          ...report,
          items: report.items.filter((item) => item.id !== itemId),
        }))
        .filter((report) => report.items.length > 0);
      if (flagPage.value && removingLastOpenItemInReport) {
        flagPage.value = { ...flagPage.value, count: Math.max(0, flagPage.value.count - 1) };
      }
    }
    toast.success(status === 'resolved' ? 'Flag resolved.' : 'Flag dismissed.');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to update flag item.'));
  } finally {
    updatingItemId.value = null;
  }
};

const editorLocation = (item: ParseFlagReviewItem, report: ParseFlagReviewReport): RouteLocationRaw =>
  buildReviewCardEditorLocation(report.card.id, route.query, {
    versionId: report.version.id,
    propertyKey: item.property_key === 'overall' ? undefined : item.property_key,
    view: 'flags',
    status: flagStatus.value,
  });

const propertyLabel = (propertyKey: ParseFlagPropertyKey): string =>
  parseFlagPropertyLabels[propertyKey] ?? propertyKey;

const versionLabel = (report: ParseFlagReviewReport): string => {
  const contentVersion = report.version.content_version?.version_number;
  return contentVersion
    ? `Printing ${report.version.version_number} · ${contentVersion}`
    : `Printing ${report.version.version_number}`;
};

const statusClass = (status: ParseFlagReviewItem['status']): string => {
  if (status === 'open') return 'theme-pill-warning';
  if (status === 'resolved') return 'theme-pill-success';
  return 'theme-pill-neutral';
};

const openItems = (group: ParseFlagReviewGroup): ParseFlagReviewItem[] =>
  group.items.filter((item) => item.status === 'open');

const groupStatusLabel = (group: ParseFlagReviewGroup): string => {
  if (group.openCount > 0) return `${group.openCount} open · ${group.items.length} flagged`;
  if (group.resolvedCount === group.items.length) return `${group.items.length} resolved`;
  if (group.dismissedCount === group.items.length) return `${group.items.length} dismissed`;
  return `${group.items.length} reviewed`;
};

const groupStatusClass = (group: ParseFlagReviewGroup): string => {
  if (group.openCount > 0) return 'theme-pill-warning';
  if (group.resolvedCount === group.items.length) return 'theme-pill-success';
  return 'theme-pill-neutral';
};

const formatDate = (value: string): string => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
};

function normalizeFlagStatus(value: string | null): FlagStatus {
  return value === 'resolved' || value === 'dismissed' || value === 'all' ? value : 'open';
}

watch(
  () => route.query,
  (query: LocationQuery) => {
    const nextView = queryString(query.view) === 'confidence' ? 'confidence' : 'flags';
    const nextStatus = normalizeFlagStatus(queryString(query.status));
    activeView.value = nextView;
    flagStatus.value = nextStatus;
    if (nextView === 'flags') {
      void loadFlagPage(1, 'replace');
    }
  },
);

watch(
  () => workspace.generation,
  () => {
    flagRequestGeneration += 1;
    loadingFlags.value = false;
    flagReports.value = [];
    flagPage.value = null;
    if (activeView.value === 'flags') {
      void loadFlagPage(1, 'replace');
    }
  },
  { flush: 'sync' },
);

onMounted(() => {
  void collection.searchCards();
  if (activeView.value === 'flags') {
    void loadFlagPage(1, 'replace');
  }
});
</script>

<style scoped>
.review-list-row + .review-list-row,
.review-report-row + .review-report-row {
  border-top-width: 1px;
}
</style>

<template>
  <section class="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
    <AppPageHeader
      :icon="ClipboardCheck"
      title="Review Queue"
      subtitle="Review low-confidence parses and user-reported parse issues."
      title-tag="h2"
      title-class="text-xl"
    >
      <template
        v-if="activeView === 'flags'"
        #bottomLeft
      >
        <div class="theme-tablist">
          <button
            v-for="status in flagStatuses"
            :key="status.value"
            class="theme-tab"
            :class="{ 'theme-tab-active': flagStatus === status.value }"
            type="button"
            @click="setFlagStatus(status.value)"
          >
            {{ status.label }}
          </button>
        </div>
      </template>

      <template #bottomRight>
        <div class="theme-tablist">
          <button
            class="theme-tab"
            :class="{ 'theme-tab-active': activeView === 'confidence' }"
            type="button"
            @click="setActiveView('confidence')"
          >
            Low Confidence
          </button>
          <button
            class="theme-tab"
            :class="{ 'theme-tab-active': activeView === 'flags' }"
            type="button"
            @click="setActiveView('flags')"
          >
            Flagged Parses
          </button>
        </div>
      </template>
    </AppPageHeader>

    <div
      v-if="activeView === 'confidence'"
      class="page-card app-scrollbar min-h-0 flex-1 overflow-y-auto"
    >
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p class="theme-section-muted text-sm font-medium">
          {{ cards.length }} loaded
        </p>
        <button
          v-if="nextPage !== null"
          class="btn-secondary"
          type="button"
          @click="loadMore"
        >
          Load more
        </button>
      </div>

      <ul class="grid gap-2">
        <li
          v-for="card in cards"
          :key="card.id"
          class="theme-card-frame theme-section-title rounded-lg px-3 py-2 text-sm"
        >
          <RouterLink
            class="theme-link font-medium"
            :to="`/cards/${card.id}/edit`"
          >
            {{ card.name }}
          </RouterLink>
          - {{ card.confidence }}
        </li>
      </ul>
    </div>

    <div
      v-else
      class="page-card app-scrollbar min-h-0 flex-1 overflow-y-auto"
    >
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p class="theme-section-muted text-sm font-medium">
          {{ flagGroups.length }} loaded · {{ flagPage?.count ?? 0 }} reports
        </p>
      </div>

      <div
        v-if="loadingFlags"
        class="theme-empty-state"
      >
        Loading flagged parses...
      </div>
      <div
        v-else-if="flagGroups.length === 0"
        class="theme-empty-state"
      >
        No flagged parse reports found.
      </div>
      <ul
        v-else
        class="grid gap-3"
      >
        <li
          v-for="group in flagGroups"
          :key="group.flagId"
          class="theme-card-frame grid gap-4 rounded-lg p-3 sm:grid-cols-[14rem_minmax(0,1fr)] lg:grid-cols-[17rem_minmax(0,1fr)]"
        >
          <RouterLink
            :to="editorLocation(group.primary, group)"
            class="mx-auto block w-64 max-w-full overflow-hidden rounded-lg sm:mx-0 sm:w-full"
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

          <div class="min-w-0">
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
                class="theme-card-frame-muted rounded-lg px-3 py-3"
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

                <div class="mt-3 grid gap-3 md:grid-cols-2">
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

                <div
                  v-if="item.status === 'open'"
                  class="theme-divider mt-3 flex flex-wrap items-center justify-end gap-2 border-t pt-3"
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
                </div>
                <p
                  v-else-if="item.review_note"
                  class="theme-section-muted mt-3 text-xs"
                >
                  Review note: {{ item.review_note }}
                </p>
              </div>
            </div>
          </div>
        </li>
      </ul>

      <div
        v-if="flagPage?.next_page"
        class="mt-4 flex justify-end"
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
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { ClipboardCheck } from 'lucide-vue-next';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { api, toAbsoluteApiUrl } from '@/api/client';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { buildReviewCardEditorLocation } from '@/composables/cards/cardReturnState';
import { useCardCollection } from '@/composables/useCardCollection';
import { useReviewSummary } from '@/composables/useReviewSummary';
import { parseFlagPropertyLabels } from '@/modules/card-detail/types';
import type { ParseFlagPropertyKey, PaginatedCardsResponse } from '@/modules/card-detail/types';
import { queryString } from '@/router/routeState';

type ReviewCard = { id: string; name: string; confidence: number };
type ReviewView = 'confidence' | 'flags';
type FlagStatus = 'open' | 'resolved' | 'dismissed' | 'all';
type UserSummary = { id: string; username: string };
type ParseFlagReviewItem = {
  id: string;
  flag_id: string;
  status: Exclude<FlagStatus, 'all'>;
  property_key: ParseFlagPropertyKey;
  captured_current_value: string;
  expected_value: string;
  note: string;
  created_at: string;
  updated_at: string;
  review_note: string;
  reviewed_at: string | null;
  reviewed_by: UserSummary | null;
};
type ParseFlagReviewReport = {
  id: string;
  note: string;
  created_at: string;
  updated_at: string;
  submitted_by: UserSummary;
  card: {
    id: string;
    label: string;
    name: string;
    image_url: string | null;
  };
  version: {
    id: string;
    version_number: number;
    is_latest: boolean;
    content_version: { id: string; version_number: string } | null;
  };
  items: ParseFlagReviewItem[];
};

type ParseFlagPage = PaginatedCardsResponse<ParseFlagReviewReport>;
type ParseFlagReviewGroup = ParseFlagReviewReport & {
  flagId: string;
  primary: ParseFlagReviewItem;
  openCount: number;
  resolvedCount: number;
  dismissedCount: number;
};

const route = useRoute();
const router = useRouter();
const activeView = ref<ReviewView>(queryString(route.query.view) === 'confidence' ? 'confidence' : 'flags');
const flagStatus = ref<FlagStatus>(normalizeFlagStatus(queryString(route.query.status)));
const flagReports = ref<ParseFlagReviewReport[]>([]);
const flagPage = ref<ParseFlagPage | null>(null);
const loadingFlags = ref(false);
const updatingItemId = ref<string | null>(null);
const filtersLoaded = ref(true);
const { decrementOpenParseFlagItemCount, loadReviewSummary } = useReviewSummary();

const collection = useCardCollection<ReviewCard>({
  buildSearchParams: () => {
    const params = new URLSearchParams();
    params.set('max_confidence', '0.8');
    return params;
  },
  filtersLoaded,
  pageSize: 100,
});
const cards = collection.cards;
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
  loadingFlags.value = true;
  try {
    const params = new URLSearchParams({
      status: flagStatus.value,
      page: String(page),
      page_size: '25',
    });
    const response = await api.get<ParseFlagPage>(`/review/parse-flags?${params.toString()}`);
    flagPage.value = response.data;
    flagReports.value = mode === 'append'
      ? [...flagReports.value, ...response.data.results]
      : response.data.results;
    if (flagStatus.value === 'open') {
      void loadReviewSummary();
    }
  } finally {
    loadingFlags.value = false;
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
    const response = await api.patch<ParseFlagReviewItem>(`/review/parse-flags/items/${itemId}`, { status });
    flagReports.value = flagReports.value.map((report) => ({
      ...report,
      items: report.items.map((item) => (item.id === itemId ? response.data : item)),
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
    propertyKey: item.property_key,
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

const extractErrorMessage = (error: unknown, fallback: string): string => {
  const maybeResponse = error as { response?: { data?: { detail?: unknown } } };
  const detail = maybeResponse.response?.data?.detail;
  return typeof detail === 'string' && detail.trim() ? detail : fallback;
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

onMounted(() => {
  void collection.searchCards();
  if (activeView.value === 'flags') {
    void loadFlagPage(1, 'replace');
  }
});
</script>

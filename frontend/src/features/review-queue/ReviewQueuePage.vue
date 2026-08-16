<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="APP_SECTION_ICONS.review"
      title="Review Queue"
      subtitle="Review classification changes and user-reported parse issues."
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
              label="Classification"
              description="Imported classifications that differ from the Card."
              :active="activeView === 'classification'"
              @click="setActiveView('classification')"
            />
            <AppSideNavItem
              label="Flagged Parses"
              description="User-submitted parse reports."
              :active="activeView === 'flags'"
              @click="setActiveView('flags')"
            />
            <template #after>
              <div class="theme-divider space-y-2 border-t pt-4">
                <p class="theme-kicker text-xs font-semibold uppercase tracking-[0.16em]">
                  {{ activeView === 'classification' ? 'Review Status' : 'Report Status' }}
                </p>
                <div class="grid gap-2">
                  <button
                    v-for="status in reviewStatuses"
                    :key="status.value"
                    class="rounded-lg border px-3 py-2 text-left text-sm font-semibold transition"
                    :class="
                      reviewStatus === status.value
                        ? 'theme-selected-surface'
                        : 'theme-card-frame theme-section-title hover:border-[var(--theme-border-strong)]'
                    "
                    type="button"
                    @click="setReviewStatus(status.value)"
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
          v-if="activeView === 'classification'"
          class="space-y-4"
        >
          <div class="theme-divider border-b pb-4">
            <h3 class="theme-section-title text-base font-semibold">
              Classification
            </h3>
            <p class="theme-section-muted mt-1 text-sm">
              {{ classificationItems.length }} loaded · {{ classificationPage?.count ?? 0 }} items
            </p>
          </div>

          <ul
            v-if="loadingClassification"
            class="theme-divider"
            aria-label="Loading classification review items"
          >
            <li
              v-for="index in 3"
              :key="`classification-loading-${index}`"
              class="review-report-row theme-divider grid gap-4 py-5 sm:grid-cols-[10rem_minmax(0,1fr)] lg:grid-cols-[12rem_minmax(0,1fr)]"
            >
              <div
                class="mx-auto aspect-[3/4] w-44 max-w-full animate-pulse rounded-lg bg-[var(--color-surface-muted)] sm:mx-0 sm:w-full"
              />
              <div class="space-y-4">
                <div class="h-5 w-48 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                <div class="grid gap-3 lg:grid-cols-3">
                  <div
                    v-for="cell in 3"
                    :key="cell"
                    class="h-24 animate-pulse rounded-lg bg-[var(--color-surface-muted)]"
                  />
                </div>
              </div>
            </li>
          </ul>

          <div
            v-else-if="classificationLoadError"
            class="theme-empty-state flex min-h-72 flex-col items-center justify-center gap-3 py-10 text-center text-sm"
            role="alert"
          >
            <div class="space-y-1">
              <h3 class="theme-section-title text-sm font-semibold">
                Classification reviews could not be loaded
              </h3>
              <p class="theme-section-muted mx-auto max-w-md leading-6">
                {{ classificationLoadError }}
              </p>
            </div>
            <button
              class="btn-secondary"
              type="button"
              @click="loadClassificationPage(1, 'replace')"
            >
              Try again
            </button>
          </div>

          <div
            v-else-if="classificationItems.length === 0"
            class="theme-section-muted flex min-h-72 items-center justify-center py-10 text-center text-sm"
          >
            <div class="space-y-1">
              <h3 class="theme-section-title text-sm font-semibold">
                No classification reviews
              </h3>
              <p class="mx-auto max-w-md leading-6">
                There are no imported classification differences in this view.
              </p>
            </div>
          </div>

          <ul
            v-else
            class="theme-divider"
          >
            <li
              v-for="item in classificationItems"
              :key="item.id"
              class="review-report-row theme-divider grid gap-4 py-5 sm:grid-cols-[10rem_minmax(0,1fr)] lg:grid-cols-[12rem_minmax(0,1fr)]"
            >
              <RouterLink
                v-if="item.card.id"
                :to="classificationEditorLocation(item)"
                class="mx-auto block w-44 max-w-full overflow-hidden rounded-lg sm:mx-0 sm:w-full"
              >
                <img
                  v-if="item.card.image_url"
                  :src="toAbsoluteApiUrl(item.card.image_url)"
                  :alt="item.card.name"
                  class="aspect-[3/4] w-full object-cover"
                >
                <div
                  v-else
                  class="theme-empty-state aspect-[3/4]"
                >
                  No image
                </div>
              </RouterLink>
              <div
                v-else
                class="mx-auto block w-44 max-w-full overflow-hidden rounded-lg sm:mx-0 sm:w-full"
              >
                <div class="theme-empty-state aspect-[3/4]">
                  No image
                </div>
              </div>

              <div class="flex h-full min-w-0 flex-col">
                <div>
                  <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0">
                      <RouterLink
                        v-if="item.card.id"
                        class="theme-link text-base font-semibold"
                        :to="classificationEditorLocation(item)"
                      >
                        {{ item.card.name }}
                      </RouterLink>
                      <span
                        v-else
                        class="theme-section-title text-base font-semibold"
                      >{{
                        item.card.name
                      }}</span>
                      <span class="theme-pill ml-2 px-2 py-0.5 text-xs">{{
                        cardPoolLabel(item.card.card_pool)
                      }}</span>
                      <p class="theme-section-muted mt-1 text-xs">
                        {{ classificationVersionLabel(item) }} · imported
                        {{ formatDate(item.created_at) }}
                      </p>
                    </div>
                    <span
                      class="theme-pill px-2.5 py-1 text-xs"
                      :class="statusClass(item.status)"
                    >{{ item.status }}</span>
                  </div>

                  <div class="mt-4 grid gap-3 lg:grid-cols-3">
                    <ClassificationSnapshot
                      label="Existing when imported"
                      :classification="item.existing_classification"
                    />
                    <ClassificationSnapshot
                      label="Inferred from this version"
                      :classification="item.inferred_classification"
                      emphasized
                    />
                    <ClassificationSnapshot
                      v-if="currentClassificationChanged(item)"
                      label="Current Card"
                      :classification="currentClassification(item)"
                    />
                  </div>

                  <div
                    v-if="inferenceSources(item).length > 0"
                    class="mt-4"
                  >
                    <p class="theme-kicker text-[11px] font-medium uppercase tracking-wide">
                      Inference Sources
                    </p>
                    <p class="theme-section-muted mt-1 text-sm">
                      {{ inferenceSources(item).join(' · ') }}
                    </p>
                  </div>

                  <p
                    v-if="item.status !== 'open'"
                    class="theme-section-muted mt-4 text-xs"
                  >
                    Reviewed{{ item.reviewed_by ? ` by ${item.reviewed_by.username}` : ''
                    }}{{ item.reviewed_at ? ` on ${formatDate(item.reviewed_at)}` : '' }}.
                    <template v-if="item.review_note">
                      {{ item.review_note }}
                    </template>
                  </p>
                </div>

                <div
                  v-if="item.status === 'open'"
                  class="theme-divider mt-auto flex flex-wrap items-center justify-end gap-2 border-t pt-3"
                >
                  <RouterLink
                    v-if="item.card.id"
                    class="btn-primary"
                    :to="classificationEditorLocation(item)"
                  >
                    Open Card
                  </RouterLink>
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="updatingClassificationId === item.id"
                    @click="updateClassificationItem(item.id, 'dismissed')"
                  >
                    Keep Existing
                  </button>
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="updatingClassificationId === item.id"
                    @click="updateClassificationItem(item.id, 'resolved')"
                  >
                    Mark Resolved
                  </button>
                </div>
              </div>
            </li>
          </ul>

          <div
            v-if="classificationPage?.next_page"
            class="flex justify-end"
          >
            <button
              class="btn-secondary"
              type="button"
              :disabled="loadingClassification"
              @click="loadClassificationPage(classificationPage.next_page, 'append')"
            >
              Load more
            </button>
          </div>
        </div>

        <div
          v-else
          class="space-y-4"
        >
          <div class="theme-divider border-b pb-4">
            <h3 class="theme-section-title text-base font-semibold">
              Flagged Parses
            </h3>
            <p class="theme-section-muted mt-1 text-sm">
              {{ flagGroups.length }} loaded · {{ flagPage?.count ?? 0 }} reports
            </p>
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
              <div
                class="mx-auto aspect-[3/4] w-44 max-w-full animate-pulse rounded-lg bg-[var(--color-surface-muted)] sm:mx-0 sm:w-full"
              />
              <div class="h-32 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
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
                :to="flagEditorLocation(group.primary, group)"
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
                        :to="flagEditorLocation(group.primary, group)"
                      >
                        {{ group.card.name }}
                      </RouterLink>
                      <span class="theme-pill ml-2 px-2 py-0.5 text-xs">{{
                        cardPoolLabel(group.card.card_pool)
                      }}</span>
                      <p class="theme-section-muted mt-1 text-xs">
                        {{ flagVersionLabel(group) }} · reported by
                        {{ group.submitted_by.username }} on {{ formatDate(group.created_at) }}
                      </p>
                    </div>
                    <span
                      class="theme-pill px-2.5 py-1 text-xs"
                      :class="groupStatusClass(group)"
                    >{{
                      groupStatusLabel(group)
                    }}</span>
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
                        >{{ item.status }}</span>
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
                  v-if="openFlagItems(group).length > 0"
                  class="theme-divider mt-auto flex flex-wrap items-center justify-end gap-2 border-t pt-3"
                >
                  <template
                    v-for="item in openFlagItems(group)"
                    :key="`actions-${item.id}`"
                  >
                    <RouterLink
                      class="btn-primary"
                      :to="flagEditorLocation(item, group)"
                    >
                      Open Editor
                    </RouterLink>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="updatingFlagItemId === item.id"
                      @click="updateFlagItem(item.id, 'dismissed')"
                    >
                      Dismiss
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="updatingFlagItemId === item.id"
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
import { useRoute, useRouter } from 'vue-router';
import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { toast } from 'vue-sonner';
import { buildReviewCardEditorLocation } from '@/domain/card-navigation/cardReturnState';
import { cardPoolLabel } from '@/domain/cards/cardPools';
import { useReviewSummary } from '@/domain/review/composables/useReviewSummary';
import { parseFlagPropertyLabels, type ParseFlagPropertyKey } from '@/domain/review/types';
import ClassificationSnapshot from '@/features/review-queue/components/ClassificationSnapshot.vue';
import {
  fetchClassificationReviewPage,
  fetchParseFlagPage,
  updateClassificationReviewItem,
  updateParseFlagItem,
} from '@/features/review-queue/api';
import type {
  CardClassificationSnapshot,
  ClassificationReviewItem,
  ClassificationReviewPage,
  FlagStatus,
  ParseFlagPage,
  ParseFlagReviewGroup,
  ParseFlagReviewItem,
  ParseFlagReviewReport,
  ReviewView,
} from '@/features/review-queue/types';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { getApiErrorMessage as extractErrorMessage } from '@/shared/api/errors';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';
import AppSideNav from '@/shared/components/app/AppSideNav.vue';
import AppSideNavItem from '@/shared/components/app/AppSideNavItem.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
import { queryString } from '@/shared/router/routeState';

const route = useRoute();
const router = useRouter();
const activeView = ref<ReviewView>(normalizeView(queryString(route.query.view)));
const reviewStatus = ref<FlagStatus>(normalizeStatus(queryString(route.query.status)));
const classificationItems = ref<ClassificationReviewItem[]>([]);
const classificationPage = ref<ClassificationReviewPage | null>(null);
const loadingClassification = ref(false);
const classificationLoadError = ref<string | null>(null);
let classificationRequestGeneration = 0;
const updatingClassificationId = ref<string | null>(null);
const flagReports = ref<ParseFlagReviewReport[]>([]);
const flagPage = ref<ParseFlagPage | null>(null);
const loadingFlags = ref(false);
let flagRequestGeneration = 0;
const updatingFlagItemId = ref<string | null>(null);
const {
  decrementOpenClassificationReviewCount,
  decrementOpenParseFlagItemCount,
  loadReviewSummary,
} = useReviewSummary();

const reviewStatuses: Array<{ value: FlagStatus; label: string }> = [
  { value: 'open', label: 'Open' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: 'all', label: 'All' },
];

const flagGroups = computed<ParseFlagReviewGroup[]>(() =>
  flagReports.value
    .flatMap((report): ParseFlagReviewGroup[] => {
      const sortedItems = [...report.items].sort((first, second) => {
        const createdAtOrder = first.created_at.localeCompare(second.created_at);
        return createdAtOrder !== 0
          ? createdAtOrder
          : propertyLabel(first.property_key).localeCompare(propertyLabel(second.property_key));
      });
      const primary = sortedItems[0];
      if (!primary) return [];
      return [
        {
          ...report,
          flagId: report.id,
          items: sortedItems,
          primary,
          openCount: sortedItems.filter((item) => item.status === 'open').length,
          resolvedCount: sortedItems.filter((item) => item.status === 'resolved').length,
          dismissedCount: sortedItems.filter((item) => item.status === 'dismissed').length,
        },
      ];
    })
    .sort((first, second) => second.created_at.localeCompare(first.created_at)),
);

const setActiveView = (view: ReviewView): void => {
  activeView.value = view;
  syncQuery();
  void loadActivePage();
};

const setReviewStatus = (status: FlagStatus): void => {
  reviewStatus.value = status;
  syncQuery();
  void loadActivePage();
};

const syncQuery = (): void => {
  void router.replace({
    path: '/review',
    query: { view: activeView.value, status: reviewStatus.value },
  });
};

const loadActivePage = async (): Promise<void> => {
  if (activeView.value === 'classification') await loadClassificationPage(1, 'replace');
  else await loadFlagPage(1, 'replace');
};

const loadClassificationPage = async (page: number, mode: 'replace' | 'append'): Promise<void> => {
  const requestGeneration = ++classificationRequestGeneration;
  const status = reviewStatus.value;
  loadingClassification.value = true;
  classificationLoadError.value = null;
  if (mode === 'replace') {
    classificationItems.value = [];
    classificationPage.value = null;
  }
  try {
    const response = await fetchClassificationReviewPage(status, page, 25);
    if (requestGeneration !== classificationRequestGeneration || status !== reviewStatus.value)
      return;
    classificationPage.value = response;
    classificationItems.value =
      mode === 'append' ? [...classificationItems.value, ...response.results] : response.results;
    if (status === 'open') void loadReviewSummary();
  } catch (error) {
    if (requestGeneration !== classificationRequestGeneration || status !== reviewStatus.value)
      return;
    classificationItems.value = [];
    classificationPage.value = null;
    classificationLoadError.value = extractErrorMessage(
      error,
      'Check your connection and try again.',
    );
  } finally {
    if (requestGeneration === classificationRequestGeneration) loadingClassification.value = false;
  }
};

const loadFlagPage = async (page: number, mode: 'replace' | 'append'): Promise<void> => {
  const requestGeneration = ++flagRequestGeneration;
  const status = reviewStatus.value;
  loadingFlags.value = true;
  try {
    const response = await fetchParseFlagPage(status, page, 25);
    if (requestGeneration !== flagRequestGeneration || status !== reviewStatus.value) return;
    flagPage.value = response;
    flagReports.value =
      mode === 'append' ? [...flagReports.value, ...response.results] : response.results;
    if (status === 'open') void loadReviewSummary();
  } finally {
    if (requestGeneration === flagRequestGeneration) loadingFlags.value = false;
  }
};

const updateClassificationItem = async (
  itemId: string,
  status: 'resolved' | 'dismissed',
): Promise<void> => {
  const previous = classificationItems.value.find((item) => item.id === itemId);
  updatingClassificationId.value = itemId;
  try {
    const response = await updateClassificationReviewItem(itemId, status);
    if (previous?.status === 'open') decrementOpenClassificationReviewCount();
    if (reviewStatus.value === 'open') {
      await loadClassificationPage(1, 'replace');
    } else {
      classificationItems.value = classificationItems.value.map((item) =>
        item.id === itemId ? response : item,
      );
    }
    toast.success(
      status === 'resolved' ? 'Classification review resolved.' : 'Existing classification kept.',
    );
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to update classification review.'));
  } finally {
    updatingClassificationId.value = null;
  }
};

const updateFlagItem = async (itemId: string, status: 'resolved' | 'dismissed'): Promise<void> => {
  const previousReport = flagReports.value.find((report) =>
    report.items.some((item) => item.id === itemId),
  );
  const previousItem = previousReport?.items.find((item) => item.id === itemId);
  const removingLastOpenItemInReport =
    reviewStatus.value === 'open' &&
    previousReport?.items.filter((item) => item.status === 'open').length === 1;
  updatingFlagItemId.value = itemId;
  try {
    const response = await updateParseFlagItem(itemId, status);
    flagReports.value = flagReports.value.map((report) => ({
      ...report,
      items: report.items.map((item) => (item.id === itemId ? response : item)),
    }));
    if (previousItem?.status === 'open') decrementOpenParseFlagItemCount();
    if (reviewStatus.value === 'open') {
      flagReports.value = flagReports.value
        .map((report) => ({ ...report, items: report.items.filter((item) => item.id !== itemId) }))
        .filter((report) => report.items.length > 0);
      if (flagPage.value && removingLastOpenItemInReport)
        flagPage.value = { ...flagPage.value, count: Math.max(0, flagPage.value.count - 1) };
    }
    toast.success(status === 'resolved' ? 'Flag resolved.' : 'Flag dismissed.');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to update flag item.'));
  } finally {
    updatingFlagItemId.value = null;
  }
};

const classificationEditorLocation = (item: ClassificationReviewItem): RouteLocationRaw => {
  if (!item.card.id) return { path: '/review' };
  return buildReviewCardEditorLocation(item.card.id, route.query, {
    versionId: item.version?.id,
    tab: 'card',
    view: 'classification',
    status: reviewStatus.value,
  });
};

const flagEditorLocation = (
  item: ParseFlagReviewItem,
  report: ParseFlagReviewReport,
): RouteLocationRaw =>
  buildReviewCardEditorLocation(report.card.id, route.query, {
    versionId: report.version.id,
    propertyKey: item.property_key === 'overall' ? undefined : item.property_key,
    view: 'flags',
    status: reviewStatus.value,
  });

const currentClassification = (item: ClassificationReviewItem): CardClassificationSnapshot => ({
  card_pool: item.card.card_pool,
  card_roles: item.card.card_roles,
  card_factions: item.card.card_factions,
  card_mana_families: item.card.card_mana_families,
});

const snapshotKey = (classification: CardClassificationSnapshot): string =>
  JSON.stringify({
    pool: classification.card_pool,
    roles: classification.card_roles,
    factions: classification.card_factions,
    mana: classification.card_mana_families,
  });

const currentClassificationChanged = (item: ClassificationReviewItem): boolean =>
  snapshotKey(currentClassification(item)) !== snapshotKey(item.existing_classification);

const inferenceSources = (item: ClassificationReviewItem): string[] => {
  const labels: string[] = [];
  const groups = [
    ['Role', item.inference_evidence.roles],
    ['Faction', item.inference_evidence.factions],
    ['Mana', item.inference_evidence.mana_families],
  ] as const;
  for (const [label, rawEvidence] of groups) {
    if (!rawEvidence || typeof rawEvidence !== 'object' || Array.isArray(rawEvidence)) continue;
    const evidence = rawEvidence as Record<string, unknown>;
    const sourceKeys = ['matched_tag_sources', 'matched_type_sources', 'matched_symbol_sources']
      .flatMap((key) => (Array.isArray(evidence[key]) ? evidence[key] : []))
      .flatMap((source) => {
        if (!source || typeof source !== 'object' || Array.isArray(source)) return [];
        const key = (source as Record<string, unknown>).key;
        return typeof key === 'string' ? [key] : [];
      });
    if (sourceKeys.length > 0) labels.push(`${label}: ${sourceKeys.join(', ')}`);
    else if (evidence.mode === 'override') labels.push(`${label}: manual import override`);
  }
  return labels;
};

const propertyLabel = (propertyKey: ParseFlagPropertyKey): string =>
  parseFlagPropertyLabels[propertyKey] ?? propertyKey;

const classificationVersionLabel = (item: ClassificationReviewItem): string => {
  if (!item.version) return 'Imported version unavailable';
  const contentVersion = item.version.content_version?.version_number;
  return contentVersion
    ? `Printing ${item.version.version_number} · ${contentVersion}`
    : `Printing ${item.version.version_number}`;
};

const flagVersionLabel = (report: ParseFlagReviewReport): string => {
  const contentVersion = report.version.content_version?.version_number;
  return contentVersion
    ? `Printing ${report.version.version_number} · ${contentVersion}`
    : `Printing ${report.version.version_number}`;
};

const statusClass = (status: 'open' | 'resolved' | 'dismissed'): string => {
  if (status === 'open') return 'theme-pill-warning';
  if (status === 'resolved') return 'theme-pill-success';
  return 'theme-pill-neutral';
};

const openFlagItems = (group: ParseFlagReviewGroup): ParseFlagReviewItem[] =>
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

function normalizeView(value: string | null): ReviewView {
  return value === 'flags' ? 'flags' : 'classification';
}

function normalizeStatus(value: string | null): FlagStatus {
  return value === 'resolved' || value === 'dismissed' || value === 'all' ? value : 'open';
}

watch(
  () => route.query,
  (query: LocationQuery) => {
    const nextView = normalizeView(queryString(query.view));
    const nextStatus = normalizeStatus(queryString(query.status));
    if (nextView === activeView.value && nextStatus === reviewStatus.value) return;
    activeView.value = nextView;
    reviewStatus.value = nextStatus;
    void loadActivePage();
  },
);

onMounted(() => {
  void loadActivePage();
});
</script>

<style scoped>
.review-report-row + .review-report-row {
  border-top-width: 1px;
}
</style>

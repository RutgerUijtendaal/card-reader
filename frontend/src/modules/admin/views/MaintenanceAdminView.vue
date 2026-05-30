<template>
  <div class="page-card flex min-h-0 flex-col space-y-4 xl:h-[calc(100vh-10rem)]">
    <div class="space-y-1">
      <h3 class="theme-section-title text-base font-semibold">
        Maintenance
      </h3>
    </div>

    <div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div class="app-scrollbar min-h-0 space-y-4 overflow-y-auto pr-1">
        <section class="theme-muted-panel p-4">
          <div class="space-y-1">
            <h4 class="theme-section-title text-sm font-semibold">
              Utility
            </h4>
            <p class="theme-section-muted text-sm">
              Safe actions that help inspect or queue work without removing data.
            </p>
          </div>

          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <button
              class="btn-secondary justify-center"
              type="button"
              :disabled="runningBackfillSuggestions"
              @click="backfillMetadataSuggestions"
            >
              {{ runningBackfillSuggestions ? 'Backfilling...' : 'Backfill Metadata Suggestions' }}
            </button>
            <button
              class="btn-secondary justify-center"
              type="button"
              :disabled="runningQueueReparse"
              @click="queueLatestReparse"
            >
              {{ runningQueueReparse ? 'Queueing...' : 'Queue Latest Reparses' }}
            </button>
            <button
              class="btn-secondary justify-center"
              type="button"
              :disabled="runningConvertCardImages"
              @click="convertCardImagesToWebp"
            >
              {{ runningConvertCardImages ? 'Converting...' : 'Convert Card Images To WebP' }}
            </button>
          </div>
        </section>

        <section class="theme-muted-panel p-4">
          <div class="space-y-1">
            <h4 class="theme-section-title text-sm font-semibold">
              Reparse By Filters
            </h4>
            <p class="theme-section-muted text-sm">
              Reuse the current card filter logic to select latest card versions, preview how many match, and queue only that subset for reparse.
            </p>
          </div>

          <div class="mt-4 space-y-4">
            <label class="field-label">
              Search
              <input
                v-model="filterQuery"
                class="input-base"
                placeholder="Name, rules text, or related metadata"
              >
            </label>

            <CardFilterSections
              v-if="filtersLoaded"
              :state="filterSectionsState"
            />
            <div
              v-else
              class="theme-section-muted text-sm"
            >
              Loading filter options...
            </div>

            <div class="flex flex-col gap-3 rounded-2xl border border-dashed border-[var(--theme-border-strong)] bg-[var(--theme-panel-subtle)]/70 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div class="space-y-1">
                <div class="theme-section-title text-sm font-semibold">
                  Selection preview
                </div>
                <div class="theme-section-muted text-sm">
                  {{ filteredReparseSummary }}
                </div>
              </div>

              <div class="flex flex-col gap-3 sm:flex-row">
                <button
                  class="btn-secondary justify-center"
                  type="button"
                  :disabled="runningPreviewCount || !hasActiveReparseFilters || !filtersLoaded"
                  @click="previewFilteredReparseCount"
                >
                  {{ runningPreviewCount ? 'Counting...' : 'Preview Match Count' }}
                </button>
                <button
                  class="btn-primary justify-center"
                  type="button"
                  :disabled="runningQueueFilteredReparse || !hasActiveReparseFilters || !filtersLoaded"
                  @click="queueFilteredReparse"
                >
                  {{ runningQueueFilteredReparse ? 'Queueing...' : 'Queue Reparses For Selection' }}
                </button>
                <button
                  class="btn-secondary justify-center"
                  type="button"
                  :disabled="!hasActiveReparseFilters"
                  @click="resetFilteredReparse"
                >
                  Reset Filters
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>

      <aside class="theme-muted-panel app-scrollbar min-h-0 overflow-y-auto p-4">
        <h4 class="theme-section-title text-sm font-semibold">
          Notes
        </h4>
        <ul class="theme-section-muted mt-3 space-y-2 text-sm">
          <li>
            Reparse queues one parser job per template using the latest known image for each card.
          </li>
          <li>
            Filtered reparse uses the same card selection rules as card search and only targets latest versions that still have a readable image.
          </li>
          <li>
            Backfill metadata suggestions rebuilds suggested tags and types from current latest card versions.
          </li>
          <li>
            WebP conversion updates canonical card image paths while keeping original files available.
          </li>
        </ul>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { api } from '@/api/client';
import CardFilterSections from '@/modules/card-search/components/CardFilterSections.vue';
import type { MaintenanceActionResponse } from '@/modules/admin/types';
import type { PaginatedCardsResponse } from '@/modules/card-detail/types';
import {
  buildCardFilterApiPayload,
  buildCardFilterApiSearchParams,
} from '@/modules/card-filters/cardFilterState';
import { useCardFilterController } from '@/modules/card-filters/useCardFilterController';

const runningBackfillSuggestions = ref(false);
const runningQueueReparse = ref(false);
const runningConvertCardImages = ref(false);
const runningPreviewCount = ref(false);
const runningQueueFilteredReparse = ref(false);
const filteredMatchCount = ref<number | null>(null);
const {
  filtersLoaded,
  filterSectionsState,
  query,
  selectionState,
  resetFilters,
  loadFilters,
} = useCardFilterController();

const filterQuery = computed({
  get: () => query.value,
  set: (value: string) => {
    query.value = value;
  },
});

const hasActiveReparseFilters = computed(
  () => buildCardFilterApiSearchParams(selectionState.value).toString().length > 0,
);
const reparseFilterSignature = computed(() =>
  buildCardFilterApiSearchParams(selectionState.value).toString(),
);

const filteredReparseSummary = computed(() => {
  if (!hasActiveReparseFilters.value) {
    return 'Add at least one filter before previewing or queueing a filtered reparse run.';
  }
  if (filteredMatchCount.value === null) {
    return 'Preview the current filter selection to see how many latest card versions will be queued.';
  }
  if (filteredMatchCount.value === 0) {
    return 'The current filter selection matches no latest card versions.';
  }
  return `${filteredMatchCount.value} latest card version${filteredMatchCount.value === 1 ? '' : 's'} currently match this selection.`;
});

const previewFilteredReparseCount = async (): Promise<void> => {
  if (runningPreviewCount.value || !hasActiveReparseFilters.value) return;
  runningPreviewCount.value = true;
  try {
    const params = buildCardFilterApiSearchParams(selectionState.value);
    params.set('page', '1');
    params.set('page_size', '1');
    const response = await api.get<PaginatedCardsResponse>('/cards', { params });
    filteredMatchCount.value = response.data.count;
    toast.success(
      response.data.count === 0
        ? 'No cards match the current filter selection.'
        : `${response.data.count} cards match the current filter selection.`,
    );
  } catch (error) {
    console.error('Preview filtered reparse count failed', error);
    toast.error(extractErrorMessage(error, 'Failed to preview filtered reparse selection.'));
  } finally {
    runningPreviewCount.value = false;
  }
};

const queueFilteredReparse = async (): Promise<void> => {
  if (runningQueueFilteredReparse.value || !hasActiveReparseFilters.value) return;
  runningQueueFilteredReparse.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>(
      '/admin/maintenance/queue-filtered-latest-reparse',
      buildCardFilterApiPayload(selectionState.value),
    );
    toast.success(response.data.message);
  } catch (error) {
    console.error('Queue filtered latest reparse failed', error);
    toast.error(extractErrorMessage(error, 'Failed to queue filtered reparses.'));
  } finally {
    runningQueueFilteredReparse.value = false;
  }
};

const resetFilteredReparse = (): void => {
  resetFilters();
  filteredMatchCount.value = null;
};

const queueLatestReparse = async (): Promise<void> => {
  if (runningQueueReparse.value) return;
  runningQueueReparse.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>(
      '/admin/maintenance/queue-latest-reparse',
    );
    toast.success(response.data.message);
  } catch (error) {
    console.error('Queue latest reparse failed', error);
    toast.error(extractErrorMessage(error, 'Failed to queue latest reparses.'));
  } finally {
    runningQueueReparse.value = false;
  }
};

const backfillMetadataSuggestions = async (): Promise<void> => {
  if (runningBackfillSuggestions.value) return;
  runningBackfillSuggestions.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>(
      '/admin/maintenance/backfill-metadata-suggestions',
    );
    toast.success(response.data.message);
  } catch (error) {
    console.error('Backfill metadata suggestions failed', error);
    toast.error(extractErrorMessage(error, 'Failed to backfill metadata suggestions.'));
  } finally {
    runningBackfillSuggestions.value = false;
  }
};

const convertCardImagesToWebp = async (): Promise<void> => {
  if (runningConvertCardImages.value) return;
  runningConvertCardImages.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>(
      '/admin/maintenance/convert-card-images-to-webp',
    );
    toast.success(response.data.message);
  } catch (error) {
    console.error('Convert card images to WebP failed', error);
    toast.error(extractErrorMessage(error, 'Failed to convert card images to WebP.'));
  } finally {
    runningConvertCardImages.value = false;
  }
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
  }
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
};

onMounted(() => {
  void loadFilters();
});

watch(reparseFilterSignature, () => {
  filteredMatchCount.value = null;
});
</script>

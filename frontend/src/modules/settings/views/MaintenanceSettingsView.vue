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
          </div>
        </section>

        <section class="theme-danger-panel">
          <div class="space-y-1">
            <h4 class="theme-danger-title text-sm font-semibold">
              Destructive Actions
            </h4>
            <p class="theme-danger-copy text-sm">
              These actions remove data or rebuild state and cannot be undone.
            </p>
          </div>

          <div class="mt-4 space-y-4">
            <label class="field-label theme-danger-title">
              Type <span class="font-semibold">RESET</span> to enable destructive actions
              <input
                v-model="confirmText"
                class="input-base theme-danger-input"
                placeholder="RESET"
                autocomplete="off"
              >
            </label>

            <label class="theme-section-title inline-flex items-center gap-2 text-sm">
              <input
                v-model="includeImages"
                type="checkbox"
              >
              <span>Also remove imported images</span>
            </label>

            <div class="grid gap-3 md:grid-cols-2">
              <button
                class="btn-danger-secondary justify-center"
                type="button"
                :disabled="!canRunActions || runningRebuild"
                @click="rebuildDatabase"
              >
                {{ runningRebuild ? 'Rebuilding...' : 'Rebuild Database' }}
              </button>
              <button
                class="btn-danger-secondary justify-center"
                type="button"
                :disabled="!canRunActions || runningClear"
                @click="clearStorage"
              >
                {{ runningClear ? 'Clearing...' : 'Clear Stored/Debug Data' }}
              </button>
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
            Backfill metadata suggestions rebuilds suggested tags and types from current latest card versions.
          </li>
          <li>
            Clear storage removes uploads and debug artifacts. Images are kept unless explicitly included.
          </li>
          <li>
            Rebuild database resets the schema and reseeds defaults.
          </li>
        </ul>

        <div
          v-if="lastRemovedPaths.length > 0"
          class="theme-card-frame mt-4 rounded-lg p-3"
        >
          <div class="theme-kicker text-xs font-semibold uppercase tracking-wide">
            Last Removed Paths
          </div>
          <ul class="theme-section-title mt-2 grid gap-1 text-xs">
            <li
              v-for="path in lastRemovedPaths"
              :key="path"
              class="break-all"
            >
              {{ path }}
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { toast } from 'vue-sonner';
import { api } from '@/api/client';
import type { MaintenanceActionResponse } from '@/modules/settings/types';

const confirmText = ref('');
const includeImages = ref(true);
const runningRebuild = ref(false);
const runningClear = ref(false);
const runningBackfillSuggestions = ref(false);
const runningQueueReparse = ref(false);
const lastRemovedPaths = ref<string[]>([]);

const canRunActions = computed(() => confirmText.value.trim() === 'RESET');

const rebuildDatabase = async (): Promise<void> => {
  if (!canRunActions.value || runningRebuild.value) return;
  runningRebuild.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>(
      '/settings/maintenance/rebuild-database',
    );
    lastRemovedPaths.value = response.data.removed_paths ?? [];
    toast.success(response.data.message);
  } catch (error) {
    console.error('Rebuild database failed', error);
    toast.error(extractErrorMessage(error, 'Failed to rebuild database.'));
  } finally {
    runningRebuild.value = false;
  }
};

const clearStorage = async (): Promise<void> => {
  if (!canRunActions.value || runningClear.value) return;
  runningClear.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>(
      '/settings/maintenance/clear-storage',
      {
        include_images: includeImages.value,
      },
    );
    lastRemovedPaths.value = response.data.removed_paths ?? [];
    toast.success(response.data.message);
  } catch (error) {
    console.error('Clear storage failed', error);
    toast.error(extractErrorMessage(error, 'Failed to clear storage data.'));
  } finally {
    runningClear.value = false;
  }
};

const queueLatestReparse = async (): Promise<void> => {
  if (runningQueueReparse.value) return;
  runningQueueReparse.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>(
      '/settings/maintenance/queue-latest-reparse',
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
      '/settings/maintenance/backfill-metadata-suggestions',
    );
    toast.success(response.data.message);
  } catch (error) {
    console.error('Backfill metadata suggestions failed', error);
    toast.error(extractErrorMessage(error, 'Failed to backfill metadata suggestions.'));
  } finally {
    runningBackfillSuggestions.value = false;
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
</script>

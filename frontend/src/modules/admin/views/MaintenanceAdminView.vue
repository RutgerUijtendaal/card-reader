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
        </ul>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { toast } from 'vue-sonner';
import { api } from '@/api/client';
import type { MaintenanceActionResponse } from '@/modules/admin/types';

const runningBackfillSuggestions = ref(false);
const runningQueueReparse = ref(false);

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

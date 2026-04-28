<template>
  <div class="page-card space-y-4">
    <div class="space-y-1">
      <h3 class="text-base font-semibold text-slate-800">
        Maintenance
      </h3>
      <p class="text-sm text-slate-600">
        Admin actions for storage, reparsing, and database recovery.
      </p>
    </div>

    <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div class="space-y-4">
        <section class="rounded-lg border border-slate-200 p-4">
          <div class="space-y-1">
            <h4 class="text-sm font-semibold text-slate-800">
              Utility
            </h4>
            <p class="text-sm text-slate-600">
              Safe actions that help inspect or queue work without removing data.
            </p>
          </div>

          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <button
              class="btn-secondary justify-center"
              type="button"
              :disabled="runningOpenStorage"
              @click="openStorageLocation"
            >
              {{ runningOpenStorage ? 'Opening...' : 'Open Storage Location' }}
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

        <section class="rounded-lg border border-red-200 bg-red-50/40 p-4">
          <div class="space-y-1">
            <h4 class="text-sm font-semibold text-red-900">
              Destructive Actions
            </h4>
            <p class="text-sm text-red-800/80">
              These actions remove data or rebuild state and cannot be undone.
            </p>
          </div>

          <div class="mt-4 space-y-4">
            <label class="field-label">
              Type <span class="font-semibold">RESET</span> to enable destructive actions
              <input
                v-model="confirmText"
                class="input-base border-red-200 focus:border-red-300 focus:ring-red-100"
                placeholder="RESET"
                autocomplete="off"
              >
            </label>

            <label class="inline-flex items-center gap-2 text-sm text-slate-700">
              <input
                v-model="includeImages"
                type="checkbox"
              >
              <span>Also remove imported images</span>
            </label>

            <div class="grid gap-3 md:grid-cols-2">
              <button
                class="btn-secondary justify-center border-red-300 text-red-700 hover:bg-red-50"
                type="button"
                :disabled="!canRunActions || runningRebuild"
                @click="rebuildDatabase"
              >
                {{ runningRebuild ? 'Rebuilding...' : 'Rebuild Database' }}
              </button>
              <button
                class="btn-secondary justify-center border-red-300 text-red-700 hover:bg-red-50"
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

      <aside class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h4 class="text-sm font-semibold text-slate-800">
          Notes
        </h4>
        <ul class="mt-3 space-y-2 text-sm text-slate-600">
          <li>
            Reparse queues one parser job per template using the latest known image for each card.
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
          class="mt-4 rounded-lg border border-slate-200 bg-white p-3"
        >
          <div class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Last Removed Paths
          </div>
          <ul class="mt-2 grid gap-1 text-xs text-slate-700">
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
import { isTauri } from '@tauri-apps/api/core';
import { computed, ref } from 'vue';
import { toast } from 'vue-sonner';
import { api } from '@/api/client';
import type {
  MaintenanceActionResponse,
  OpenStorageLocationResponse,
} from '@/modules/settings/types';

const confirmText = ref('');
const includeImages = ref(true);
const runningRebuild = ref(false);
const runningClear = ref(false);
const runningOpenStorage = ref(false);
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

const openStorageLocation = async (): Promise<void> => {
  if (runningOpenStorage.value) return;
  runningOpenStorage.value = true;
  try {
    const response = await api.post<OpenStorageLocationResponse>(
      '/settings/maintenance/open-storage-location',
    );
    const path = response.data.path;

    if (!isTauri()) {
      const opened = tryOpenPathInBrowser(path);
      if (!opened) {
        await tryCopyPathToClipboard(path);
        toast.success(response.data.message, {
          description: `Path copied: ${path}`,
        });
        return;
      }
    }

    toast.success(response.data.message, {
      description: path,
    });
  } catch (error) {
    console.error('Open storage location failed', error);
    toast.error(extractErrorMessage(error, 'Failed to open storage location.'));
  } finally {
    runningOpenStorage.value = false;
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

const tryOpenPathInBrowser = (path: string): boolean => {
  const normalized = path.replaceAll('\\', '/');
  const fileUrl = normalized.startsWith('/') ? `file://${normalized}` : `file:///${normalized}`;
  const openedWindow = window.open(fileUrl, '_blank', 'noopener,noreferrer');
  return openedWindow !== null;
};

const tryCopyPathToClipboard = async (path: string): Promise<void> => {
  if (!navigator.clipboard?.writeText) return;
  try {
    await navigator.clipboard.writeText(path);
  } catch {
    // no-op: clipboard may be blocked by browser permissions.
  }
};
</script>

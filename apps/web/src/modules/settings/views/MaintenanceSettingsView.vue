<template>
  <div class="page-card space-y-4">
    <h3 class="text-base font-semibold text-slate-800">
      Maintenance
    </h3>
    <p class="text-sm text-slate-600">
      These actions are destructive and cannot be undone.
    </p>

    <button
      class="btn-secondary w-fit"
      type="button"
      :disabled="runningOpenStorage"
      @click="openStorageLocation"
    >
      {{ runningOpenStorage ? 'Opening...' : 'Open Storage Location' }}
    </button>

    <label class="field-label">
      Type <span class="font-semibold">RESET</span> to enable maintenance actions
      <input
        v-model="confirmText"
        class="input-base"
        placeholder="RESET"
        autocomplete="off"
      >
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

    <label class="inline-flex items-center gap-2 text-sm text-slate-700">
      <input
        v-model="includeImages"
        type="checkbox"
      >
      <span>Also remove imported images</span>
    </label>

    <ul
      v-if="lastRemovedPaths.length > 0"
      class="grid gap-1 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700"
    >
      <li class="font-semibold text-slate-800">
        Last removed paths:
      </li>
      <li
        v-for="path in lastRemovedPaths"
        :key="path"
        class="break-all"
      >
        {{ path }}
      </li>
    </ul>
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

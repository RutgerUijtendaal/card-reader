<template>
  <section class="space-y-6">
    <div class="page-card space-y-2">
      <h2 class="flex items-center gap-2 text-xl font-semibold text-slate-900">
        <Settings class="h-5 w-5 text-slate-500" />
        <span>Settings</span>
      </h2>
      <p class="text-sm text-slate-600">
        Maintenance tools for local development data.
      </p>
    </div>

    <div class="page-card space-y-4">
      <h3 class="text-base font-semibold text-slate-800">Maintenance</h3>
      <p class="text-sm text-slate-600">
        These actions are destructive and cannot be undone.
      </p>

      <label class="field-label">
        Type <span class="font-semibold">RESET</span> to enable maintenance actions
        <input
          v-model="confirmText"
          class="input-base"
          placeholder="RESET"
          autocomplete="off"
        />
      </label>

      <div class="grid gap-3 md:grid-cols-2">
        <button
          class="btn-secondary justify-center border-red-300 text-red-700 hover:bg-red-50"
          type="button"
          :disabled="!canRunActions || runningRebuild"
          @click="rebuildDatabase"
        >
          {{ runningRebuild ? 'Rebuilding…' : 'Rebuild Database' }}
        </button>

        <button
          class="btn-secondary justify-center border-red-300 text-red-700 hover:bg-red-50"
          type="button"
          :disabled="!canRunActions || runningClear"
          @click="clearStorage"
        >
          {{ runningClear ? 'Clearing…' : 'Clear Stored/Debug Data' }}
        </button>
      </div>

      <label class="inline-flex items-center gap-2 text-sm text-slate-700">
        <input v-model="includeImages" type="checkbox" />
        <span>Also remove imported images</span>
      </label>

      <ul v-if="lastRemovedPaths.length > 0" class="grid gap-1 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
        <li class="font-semibold text-slate-800">Last removed paths:</li>
        <li v-for="path in lastRemovedPaths" :key="path" class="break-all">{{ path }}</li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Settings } from 'lucide-vue-next';
import { toast } from 'vue-sonner';
import { api } from '@/api/client';

type MaintenanceActionResponse = {
  message: string;
  removed_paths: string[];
};

const confirmText = ref('');
const includeImages = ref(true);
const runningRebuild = ref(false);
const runningClear = ref(false);
const lastRemovedPaths = ref<string[]>([]);

const canRunActions = computed(() => confirmText.value.trim() === 'RESET');

const rebuildDatabase = async (): Promise<void> => {
  if (!canRunActions.value || runningRebuild.value) {
    return;
  }

  runningRebuild.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>('/settings/maintenance/rebuild-database');
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
  if (!canRunActions.value || runningClear.value) {
    return;
  }

  runningClear.value = true;
  try {
    const response = await api.post<MaintenanceActionResponse>('/settings/maintenance/clear-storage', {
      include_images: includeImages.value
    });
    lastRemovedPaths.value = response.data.removed_paths ?? [];
    toast.success(response.data.message);
  } catch (error) {
    console.error('Clear storage failed', error);
    toast.error(extractErrorMessage(error, 'Failed to clear storage data.'));
  } finally {
    runningClear.value = false;
  }
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }
  }
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
};
</script>

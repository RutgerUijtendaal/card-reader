<template>
  <section class="flex min-h-0 flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-4 border-b border-slate-200 pb-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
          {{ isCreatingNew ? 'Create' : 'Edit' }} {{ kindItemLabel(selectedKind) }}
        </p>
        <h4 class="mt-2 text-lg font-semibold text-slate-900">
          {{ title }}
        </h4>
      </div>

      <div
        v-if="!isCreatingNew"
        class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600"
      >
        <div class="font-semibold text-slate-700">
          Existing entry
        </div>
        <div class="mt-1">
          Key: <span class="font-mono text-[11px]">{{ editorEntry.key }}</span>
        </div>
      </div>
    </div>

    <div class="mt-5 min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
      <CatalogEntryForm
        :kind="selectedKind"
        :entry="editorEntry"
        :advanced-open="true"
        :show-advanced-toggle="false"
        :key-disabled="!isCreatingNew"
        :uploading-asset="uploadingAsset"
        :detection-config-example="detectionConfigExample"
        :reference-assets-example="referenceAssetsExample"
        @update:entry="emit('update:entry', $event)"
        @upload-asset="emit('upload-asset')"
      />
    </div>

    <div class="mt-5 flex flex-col gap-3 border-t border-slate-200 bg-white pt-4 sm:flex-row sm:items-center sm:justify-between">
      <button
        v-if="!isCreatingNew"
        class="btn-secondary"
        type="button"
        @click="emit('create-new')"
      >
        New {{ kindItemLabel(selectedKind) }}
      </button>
      <div
        v-else
        class="text-sm text-slate-500"
      >
        New entries use the same editor as existing ones.
      </div>

      <div class="flex flex-col gap-3 sm:flex-row">
        <button
          v-if="!isCreatingNew && selectedRow"
          class="rounded-lg border border-rose-300 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          :disabled="deletingEntryIds.has(selectedRow.id)"
          @click="emit('request-delete', selectedRow)"
        >
          {{ deletingEntryIds.has(selectedRow.id) ? 'Deleting...' : 'Delete' }}
        </button>
        <button
          class="btn-primary"
          type="button"
          :disabled="creatingEntry || savingCurrentEntry"
          @click="handlePrimaryAction"
        >
          {{ actionLabel }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import CatalogEntryForm from '@/modules/settings/components/CatalogEntryForm.vue';
import type {
  CatalogFormEntry,
  CatalogKind,
  CatalogRow,
} from '@/modules/settings/types';

const props = defineProps<{
  selectedKind: CatalogKind;
  selectedRow: CatalogRow | null;
  isCreatingNew: boolean;
  editorEntry: CatalogFormEntry;
  creatingEntry: boolean;
  savingCurrentEntry: boolean;
  deletingEntryIds: Set<string>;
  uploadingAsset: boolean;
  detectionConfigExample: string;
  referenceAssetsExample: string;
  kindItemLabel: (kind: CatalogKind) => string;
}>();

const emit = defineEmits<{
  (e: 'create'): void;
  (e: 'save'): void;
  (e: 'create-new'): void;
  (e: 'upload-asset'): void;
  (e: 'update:entry', entry: CatalogFormEntry): void;
  (e: 'request-delete', entry: CatalogRow): void;
}>();

const title = computed(() => {
  if (props.isCreatingNew) {
    return `${props.kindItemLabel(props.selectedKind)} details`;
  }

  return props.selectedRow?.label || props.selectedRow?.key || 'Untitled entry';
});

const actionLabel = computed(() => {
  if (props.isCreatingNew) {
    return props.creatingEntry ? 'Creating...' : `Create ${props.kindItemLabel(props.selectedKind)}`;
  }

  return props.savingCurrentEntry ? 'Saving...' : 'Save Changes';
});

const handlePrimaryAction = (): void => {
  if (props.isCreatingNew) {
    emit('create');
    return;
  }

  emit('save');
};
</script>

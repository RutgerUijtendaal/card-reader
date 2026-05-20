<template>
  <section class="flex min-h-0 flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-950/55">
    <div class="flex flex-col gap-4 border-b border-slate-200 pb-4 dark:border-slate-700 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="theme-kicker text-xs font-medium uppercase tracking-[0.18em]">
          {{ isCreatingNew ? 'Create' : 'Edit' }} {{ kindItemLabel(selectedKind) }}
        </p>
        <h4 class="theme-section-title mt-2 text-lg font-semibold">
          {{ title }}
        </h4>
      </div>

      <div
        v-if="!isCreatingNew"
        class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
      >
        <div class="font-semibold text-slate-700 dark:text-slate-100">
          Existing entry
        </div>
        <div class="mt-1">
          Key: <span class="font-mono text-[11px]">{{ editorEntry.key }}</span>
        </div>
      </div>
    </div>

    <div class="app-scrollbar mt-5 min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
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

      <div
        v-if="!isCreatingNew"
        class="theme-muted-panel"
      >
        <div class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
          Linked cards
        </div>
        <div class="theme-section-muted mt-1 text-sm">
          {{ linkedCardCount }} cards currently use this {{ kindItemLabel(selectedKind).toLowerCase() }}.
        </div>
        <div class="mt-4">
          <CatalogLinkedCardsGrid
            :cards="linkedCards"
            :empty-message="`No linked cards found for this ${kindItemLabel(selectedKind).toLowerCase()}.`"
          />
        </div>
      </div>
    </div>

    <div class="mt-5 flex flex-col gap-3 border-t border-slate-200 bg-white pt-4 dark:border-slate-700 dark:bg-transparent sm:flex-row sm:items-center sm:justify-between">
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
        class="theme-section-muted text-sm"
      >
      </div>

      <div class="flex flex-col gap-3 sm:flex-row">
        <button
          v-if="!isCreatingNew && selectedRow"
          class="btn-danger-secondary"
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
import CatalogLinkedCardsGrid from '@/modules/settings/components/CatalogLinkedCardsGrid.vue';
import CatalogEntryForm from '@/modules/settings/components/CatalogEntryForm.vue';
import type {
  CatalogFormEntry,
  CatalogKind,
  CatalogRow,
  LinkedCardPreview,
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
  linkedCards: LinkedCardPreview[];
  linkedCardCount: number;
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

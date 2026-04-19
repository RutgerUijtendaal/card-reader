<template>
  <div class="rounded-lg border border-slate-200 p-3">
    <h4 class="mb-3 text-sm font-semibold text-slate-800">
      Create {{ kindLabel(selectedKind).toLowerCase() }} entry
    </h4>

    <CatalogEntryForm
      :kind="selectedKind"
      :entry="newEntry"
      :advanced-open="true"
      :show-advanced-toggle="false"
      :detector-type-options="detectorTypeOptions"
      :uploading-asset="uploadingCreateAsset"
      :detection-config-example="detectionConfigExample"
      :reference-assets-example="referenceAssetsExample"
      @update:entry="emit('update:new-entry', $event)"
      @upload-asset="emit('upload-create-asset')"
    />

    <div class="mt-3">
      <button
        class="btn-primary"
        type="button"
        :disabled="creatingEntry"
        @click="emit('create')"
      >
        {{ creatingEntry ? 'Creating...' : 'Create Entry' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import CatalogEntryForm from '@/modules/settings/components/CatalogEntryForm.vue';
import type { CatalogFormEntry, CatalogKind, SymbolDetectorOption } from '@/modules/settings/types';

defineProps<{
  selectedKind: CatalogKind;
  newEntry: CatalogFormEntry;
  kindLabel: (kind: CatalogKind) => string;
  creatingEntry: boolean;
  uploadingCreateAsset: boolean;
  detectorTypeOptions: SymbolDetectorOption[];
  detectionConfigExample: string;
  referenceAssetsExample: string;
}>();

const emit = defineEmits<{
  (e: 'create'): void;
  (e: 'upload-create-asset'): void;
  (e: 'update:new-entry', entry: CatalogFormEntry): void;
}>();
</script>

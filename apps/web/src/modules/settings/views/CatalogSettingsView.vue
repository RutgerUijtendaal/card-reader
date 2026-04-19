<template>
  <div class="page-card space-y-4">
    <h3 class="text-base font-semibold text-slate-800">
      Catalog
    </h3>
    <p class="text-sm text-slate-600">
      Manage keywords, tags, symbols, and types.
    </p>

    <div class="grid grid-cols-[220px_minmax(0,1fr)] gap-4">
      <CatalogKindSidebar
        :catalog-kinds="catalogKinds"
        :selected-kind="selectedKind"
        :kind-label="kindLabel"
        @select="selectKind"
      />

      <div class="space-y-4">
        <CatalogCreateSection
          :selected-kind="selectedKind"
          :new-entry="newEntry"
          :kind-label="kindLabel"
          :creating-entry="creatingEntry"
          :uploading-create-asset="uploadingCreateAsset"
          :detector-type-options="detectorTypeOptions"
          :detection-config-example="detectionConfigExample"
          :reference-assets-example="referenceAssetsExample"
          @create="createEntry"
          @update:new-entry="setNewEntry"
          @upload-create-asset="pickAndUploadCreateAsset"
        />

        <CatalogEntriesSection
          :selected-kind="selectedKind"
          :current-rows="currentRows"
          :kind-label="kindLabel"
          :saving-entry-ids="savingEntryIds"
          :deleting-entry-ids="deletingEntryIds"
          :uploading-entry-asset-ids="uploadingEntryAssetIds"
          :detector-type-options="detectorTypeOptions"
          :detection-config-example="detectionConfigExample"
          :reference-assets-example="referenceAssetsExample"
          :is-entry-advanced-open="isEntryAdvancedOpen"
          @save="(entry) => updateEntry(selectedKind, entry)"
          @request-delete="(entry) => openDeleteModal(selectedKind, entry)"
          @upload-entry-asset="pickAndUploadEntryAsset"
          @toggle-advanced="toggleEntryAdvanced"
          @replace-entry="replaceEntry"
        />
      </div>
    </div>
  </div>

  <ConfirmModal
    :open="deleteModal.open"
    title="Delete Entry"
    :message="deleteModalMessage"
    confirm-label="Delete"
    cancel-label="Cancel"
    :loading="deleteModal.loading"
    loading-label="Deleting..."
    @cancel="closeDeleteModal"
    @confirm="confirmDeleteEntry"
  />
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import CatalogCreateSection from '@/modules/settings/components/CatalogCreateSection.vue';
import CatalogEntriesSection from '@/modules/settings/components/CatalogEntriesSection.vue';
import CatalogKindSidebar from '@/modules/settings/components/CatalogKindSidebar.vue';
import {
  detectionConfigExample,
  kindLabel,
  referenceAssetsExample,
  useCatalogSettings
} from '@/modules/settings/composables/useCatalogSettings';

const {
  catalogKinds,
  selectedKind,
  currentRows,
  newEntry,
  savingEntryIds,
  deletingEntryIds,
  creatingEntry,
  uploadingCreateAsset,
  uploadingEntryAssetIds,
  detectorTypeOptions,
  deleteModal,
  deleteModalMessage,
  selectKind,
  isEntryAdvancedOpen,
  toggleEntryAdvanced,
  loadCatalog,
  createEntry,
  setNewEntry,
  updateEntry,
  replaceEntry,
  openDeleteModal,
  closeDeleteModal,
  confirmDeleteEntry,
  pickAndUploadCreateAsset,
  pickAndUploadEntryAsset
} = useCatalogSettings();

onMounted(() => {
  void loadCatalog();
});
</script>

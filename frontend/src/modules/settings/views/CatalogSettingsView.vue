<template>
  <div class="page-card flex min-h-0 flex-col space-y-4 xl:h-[calc(100vh-10rem)]">
    <h3 class="theme-section-title text-base font-semibold">
      Catalog
    </h3>

    <div class="grid min-h-0 flex-1 gap-4 xl:grid-cols-[220px_minmax(0,340px)_minmax(0,1fr)]">
      <CatalogKindSidebar
        :catalog-kind-groups="catalogKindGroups"
        :selected-kind="selectedKind"
        :kind-label="kindLabel"
        @select="selectKind"
      />

      <CatalogEntriesSection
        :selected-kind="selectedKind"
        :search-term="currentSearchTerm"
        :total-count="allCurrentRows.length"
        :current-rows="currentRows"
        :selected-entry-id="selectedEntryId"
        :kind-label="kindLabel"
        :kind-item-label="kindItemLabel"
        :can-create="canCreateSelectedKind"
        @update:search-term="setSearchTerm"
        @create-new="startCreateEntry"
        @select-entry="selectEntry"
      />

      <CatalogDetailSection
        v-if="!isSuggestedKind"
        :selected-kind="selectedKind"
        :selected-row="selectedKnownRow"
        :is-creating-new="isCreatingNew"
        :editor-entry="editorEntry"
        :creating-entry="creatingEntry"
        :saving-current-entry="selectedEntryId ? savingEntryIds.has(selectedEntryId) : false"
        :deleting-entry-ids="deletingEntryIds"
        :uploading-asset="uploadingAsset"
        :detection-config-example="detectionConfigExample"
        :reference-assets-example="referenceAssetsExample"
        :kind-item-label="kindItemLabel"
        :linked-cards="selectedKnownRow?.linked_cards ?? []"
        :linked-card-count="selectedKnownRow?.linked_card_count ?? 0"
        @create="createEntry"
        @save="updateSelectedEntry"
        @create-new="startCreateEntry"
        @update:entry="setEditorEntry"
        @request-delete="(entry) => openDeleteModal(selectedKind, entry)"
        @upload-asset="pickAndUploadAsset"
      />

      <CatalogSuggestionDetailSection
        v-else
        :selected-kind="selectedKind"
        :selected-row="selectedSuggestionRow"
        :existing-options="existingSuggestionOptions"
        :existing-target-id="suggestionExistingTargetId"
        :new-label="suggestionNewLabel"
        :new-key="suggestionNewKey"
        :action-loading="suggestionActionLoading"
        :kind-item-label="kindItemLabel"
        @update:existing-target-id="setSuggestionExistingTargetId"
        @update:new-label="setSuggestionNewLabel"
        @update:new-key="setSuggestionNewKey"
        @accept-existing="acceptSelectedSuggestionToExisting"
        @accept-new="acceptSelectedSuggestionAsNew"
        @reject="rejectSelectedSuggestion"
      />
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
import CatalogDetailSection from '@/modules/settings/components/CatalogDetailSection.vue';
import CatalogEntriesSection from '@/modules/settings/components/CatalogEntriesSection.vue';
import CatalogKindSidebar from '@/modules/settings/components/CatalogKindSidebar.vue';
import CatalogSuggestionDetailSection from '@/modules/settings/components/CatalogSuggestionDetailSection.vue';
import {
  detectionConfigExample,
  kindItemLabel,
  kindLabel,
  referenceAssetsExample,
  useCatalogSettings,
} from '@/modules/settings/composables/useCatalogSettings';

const {
  catalogKindGroups,
  selectedKind,
  allCurrentRows,
  currentRows,
  currentSearchTerm,
  selectedEntryId,
  selectedKnownRow,
  selectedSuggestionRow,
  isCreatingNew,
  isSuggestedKind,
  canCreateSelectedKind,
  editorEntry,
  existingSuggestionOptions,
  suggestionExistingTargetId,
  suggestionNewLabel,
  suggestionNewKey,
  suggestionActionLoading,
  setSuggestionExistingTargetId,
  setSuggestionNewLabel,
  setSuggestionNewKey,
  savingEntryIds,
  deletingEntryIds,
  creatingEntry,
  uploadingAsset,
  deleteModal,
  deleteModalMessage,
  selectKind,
  setSearchTerm,
  loadCatalog,
  startCreateEntry,
  selectEntry,
  createEntry,
  setEditorEntry,
  updateSelectedEntry,
  openDeleteModal,
  closeDeleteModal,
  confirmDeleteEntry,
  pickAndUploadAsset,
  acceptSelectedSuggestionToExisting,
  acceptSelectedSuggestionAsNew,
  rejectSelectedSuggestion,
} = useCatalogSettings();

onMounted(() => {
  void loadCatalog();
});
</script>

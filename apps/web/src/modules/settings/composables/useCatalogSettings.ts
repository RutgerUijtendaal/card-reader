import { computed, ref, watch } from 'vue';
import {
  CATALOG_KINDS,
  catalogRowToFormEntry,
  detectionConfigExample,
  kindItemLabel,
  kindLabel,
  referenceAssetsExample,
} from './catalogSettingsUtils';
import { useCatalogData } from './useCatalogData';
import { useCatalogEntryActions } from './useCatalogEntryActions';
import { useCatalogEntryForm } from './useCatalogEntryForm';
import { useSymbolAssetUpload } from './useSymbolAssetUpload';

export { detectionConfigExample, kindItemLabel, kindLabel, referenceAssetsExample };

export const useCatalogSettings = () => {
  const { newEntry: editorEntry, resetNewEntryForm: resetEditorEntry, setNewEntry: setEditorEntry } =
    useCatalogEntryForm();
  const catalogData = useCatalogData(resetEditorEntry);
  const selectedEntryId = ref<string | null>(null);
  const isCreatingNew = computed(() => selectedEntryId.value === null);

  const selectedRow = computed(() =>
    selectedEntryId.value
      ? catalogData.allCurrentRows.value.find((row) => row.id === selectedEntryId.value) ?? null
      : null,
  );

  const startCreateEntry = (): void => {
    selectedEntryId.value = null;
    resetEditorEntry();
  };

  const selectEntry = (entryId: string): void => {
    const row = catalogData.allCurrentRows.value.find((item) => item.id === entryId);
    if (!row) return;
    selectedEntryId.value = row.id;
    setEditorEntry(catalogRowToFormEntry(row));
  };

  const selectKind = (kind: (typeof CATALOG_KINDS)[number]): void => {
    catalogData.selectKind(kind);
    startCreateEntry();
  };

  watch(selectedRow, (row) => {
    if (row) {
      setEditorEntry(catalogRowToFormEntry(row));
      return;
    }

    if (selectedEntryId.value) {
      startCreateEntry();
    }
  });

  const entryActions = useCatalogEntryActions({
    selectedKind: catalogData.selectedKind,
    editorEntry,
    selectedEntryId,
    loadCatalog: catalogData.loadCatalog,
    resetEditorEntry,
  });
  const symbolAssetUpload = useSymbolAssetUpload(editorEntry);

  return {
    catalogKinds: CATALOG_KINDS,
    selectedKind: catalogData.selectedKind,
    catalog: catalogData.catalog,
    currentSearchTerm: catalogData.currentSearchTerm,
    allCurrentRows: catalogData.allCurrentRows,
    currentRows: catalogData.currentRows,
    selectedEntryId,
    selectedRow,
    isCreatingNew,
    editorEntry,
    savingEntryIds: entryActions.savingEntryIds,
    deletingEntryIds: entryActions.deletingEntryIds,
    creatingEntry: entryActions.creatingEntry,
    uploadingAsset: symbolAssetUpload.uploadingAsset,
    deleteModal: entryActions.deleteModal,
    deleteModalMessage: entryActions.deleteModalMessage,
    kindItemLabel,
    kindLabel,
    selectKind,
    setSearchTerm: catalogData.setSearchTerm,
    loadCatalog: catalogData.loadCatalog,
    startCreateEntry,
    selectEntry,
    createEntry: entryActions.createEntry,
    setEditorEntry,
    updateSelectedEntry: entryActions.updateSelectedEntry,
    openDeleteModal: entryActions.openDeleteModal,
    closeDeleteModal: entryActions.closeDeleteModal,
    confirmDeleteEntry: entryActions.confirmDeleteEntry,
    pickAndUploadAsset: symbolAssetUpload.pickAndUploadAsset,
  };
};

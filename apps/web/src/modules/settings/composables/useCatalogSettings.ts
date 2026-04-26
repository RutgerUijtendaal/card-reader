import { SYMBOL_DETECTOR_OPTIONS } from '@/modules/settings/types';
import {
  CATALOG_KINDS,
  detectionConfigExample,
  kindLabel,
  referenceAssetsExample,
} from './catalogSettingsUtils';
import { useCatalogData } from './useCatalogData';
import { useCatalogEntryActions } from './useCatalogEntryActions';
import { useCatalogEntryForm } from './useCatalogEntryForm';
import { useSymbolAssetUpload } from './useSymbolAssetUpload';

export { detectionConfigExample, kindLabel, referenceAssetsExample };

export const useCatalogSettings = () => {
  const { newEntry, resetNewEntryForm, setNewEntry } = useCatalogEntryForm();
  const catalogData = useCatalogData(resetNewEntryForm);
  const entryActions = useCatalogEntryActions({
    selectedKind: catalogData.selectedKind,
    newEntry,
    loadCatalog: catalogData.loadCatalog,
    resetNewEntryForm,
  });
  const symbolAssetUpload = useSymbolAssetUpload(newEntry);

  return {
    catalogKinds: CATALOG_KINDS,
    selectedKind: catalogData.selectedKind,
    catalog: catalogData.catalog,
    currentRows: catalogData.currentRows,
    newEntry,
    savingEntryIds: entryActions.savingEntryIds,
    deletingEntryIds: entryActions.deletingEntryIds,
    creatingEntry: entryActions.creatingEntry,
    uploadingCreateAsset: symbolAssetUpload.uploadingCreateAsset,
    uploadingEntryAssetIds: symbolAssetUpload.uploadingEntryAssetIds,
    detectorTypeOptions: SYMBOL_DETECTOR_OPTIONS,
    advancedEntryIds: entryActions.advancedEntryIds,
    deleteModal: entryActions.deleteModal,
    deleteModalMessage: entryActions.deleteModalMessage,
    kindLabel,
    selectKind: catalogData.selectKind,
    isEntryAdvancedOpen: entryActions.isEntryAdvancedOpen,
    toggleEntryAdvanced: entryActions.toggleEntryAdvanced,
    loadCatalog: catalogData.loadCatalog,
    createEntry: entryActions.createEntry,
    setNewEntry,
    updateEntry: entryActions.updateEntry,
    replaceEntry: catalogData.replaceEntry,
    openDeleteModal: entryActions.openDeleteModal,
    closeDeleteModal: entryActions.closeDeleteModal,
    confirmDeleteEntry: entryActions.confirmDeleteEntry,
    pickAndUploadCreateAsset: symbolAssetUpload.pickAndUploadCreateAsset,
    pickAndUploadEntryAsset: symbolAssetUpload.pickAndUploadEntryAsset,
  };
};

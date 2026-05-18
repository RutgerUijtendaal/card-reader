import { computed, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  acceptSuggestionAsNew,
  acceptSuggestionToExisting,
  rejectSuggestion,
} from '@/modules/settings/api/catalog';
import type { SuggestionRecord, TagRecord, TypeRecord } from '@/modules/settings/types';
import {
  CATALOG_KIND_GROUPS,
  CATALOG_KINDS,
  catalogRowToFormEntry,
  detectionConfigExample,
  isKnownCatalogKind,
  isSuggestedCatalogKind,
  kindItemLabel,
  kindLabel,
  referenceAssetsExample,
} from './catalogSettingsUtils';
import { extractErrorMessage } from './catalogSettingsUtils';
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
  const isSuggestedKind = computed(() => isSuggestedCatalogKind(catalogData.selectedKind.value));
  const canCreateSelectedKind = computed(() => isKnownCatalogKind(catalogData.selectedKind.value));
  const suggestionExistingTargetId = ref('');
  const suggestionNewLabel = ref('');
  const suggestionNewKey = ref('');
  const suggestionActionLoading = ref(false);

  const selectedRow = computed(() =>
    selectedEntryId.value
      ? catalogData.allCurrentRows.value.find((row) => row.id === selectedEntryId.value) ?? null
      : null,
  );
  const selectedSuggestionRow = computed(() =>
    selectedRow.value && 'status' in selectedRow.value ? (selectedRow.value as SuggestionRecord) : null,
  );
  const selectedSuggestionKind = computed<'tag' | 'type' | null>(() => {
    const row = selectedSuggestionRow.value;
    return row?.kind ?? null;
  });
  const existingSuggestionOptions = computed<TagRecord[] | TypeRecord[]>(() => {
    if (catalogData.selectedKind.value === 'suggested-tags') {
      return catalogData.catalog.tags;
    }
    if (catalogData.selectedKind.value === 'suggested-types') {
      return catalogData.catalog.types;
    }
    return [];
  });

  const startCreateEntry = (): void => {
    selectedEntryId.value = null;
    resetEditorEntry();
  };

  const selectEntry = (entryId: string): void => {
    const row = catalogData.allCurrentRows.value.find((item) => item.id === entryId);
    if (!row) return;
    selectedEntryId.value = row.id;
    if ('status' in row) {
      suggestionExistingTargetId.value = '';
      suggestionNewLabel.value = row.display_value;
      suggestionNewKey.value = '';
      return;
    }
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

  const reloadSuggestions = async (): Promise<void> => {
    await catalogData.loadCatalog();
    if (!selectedEntryId.value) {
      return;
    }
    const row = catalogData.allCurrentRows.value.find((item) => item.id === selectedEntryId.value);
    if (row && 'status' in row) {
      suggestionNewLabel.value = row.display_value;
    }
  };

  const acceptSelectedSuggestionToExisting = async (targetId: string): Promise<void> => {
    if (!selectedSuggestionRow.value || !selectedSuggestionKind.value || suggestionActionLoading.value) return;
    suggestionActionLoading.value = true;
    try {
      await acceptSuggestionToExisting(selectedSuggestionKind.value, selectedSuggestionRow.value.id, { target_id: targetId });
      toast.success('Suggestion accepted.');
      await reloadSuggestions();
    } catch (error) {
      toast.error(extractErrorMessage(error, 'Failed to accept suggestion.'));
    } finally {
      suggestionActionLoading.value = false;
    }
  };

  const acceptSelectedSuggestionAsNew = async (): Promise<void> => {
    if (!selectedSuggestionRow.value || !selectedSuggestionKind.value || suggestionActionLoading.value) return;
    suggestionActionLoading.value = true;
    try {
      await acceptSuggestionAsNew(selectedSuggestionKind.value, selectedSuggestionRow.value.id, {
        label: suggestionNewLabel.value.trim() || undefined,
        key: suggestionNewKey.value.trim() || undefined,
      });
      toast.success('Suggestion accepted.');
      await reloadSuggestions();
    } catch (error) {
      toast.error(extractErrorMessage(error, 'Failed to accept suggestion.'));
    } finally {
      suggestionActionLoading.value = false;
    }
  };

  const rejectSelectedSuggestion = async (): Promise<void> => {
    if (!selectedSuggestionRow.value || !selectedSuggestionKind.value || suggestionActionLoading.value) return;
    suggestionActionLoading.value = true;
    try {
      await rejectSuggestion(selectedSuggestionKind.value, selectedSuggestionRow.value.id);
      toast.success('Suggestion rejected.');
      await reloadSuggestions();
    } catch (error) {
      toast.error(extractErrorMessage(error, 'Failed to reject suggestion.'));
    } finally {
      suggestionActionLoading.value = false;
    }
  };

  const setSuggestionExistingTargetId = (value: string): void => {
    suggestionExistingTargetId.value = value;
  };

  const setSuggestionNewLabel = (value: string): void => {
    suggestionNewLabel.value = value;
  };

  const setSuggestionNewKey = (value: string): void => {
    suggestionNewKey.value = value;
  };

  return {
    catalogKinds: CATALOG_KINDS,
    catalogKindGroups: CATALOG_KIND_GROUPS.map((group) => ({ label: group.label, kinds: [...group.kinds] })),
    selectedKind: catalogData.selectedKind,
    catalog: catalogData.catalog,
    currentSearchTerm: catalogData.currentSearchTerm,
    allCurrentRows: catalogData.allCurrentRows,
    currentRows: catalogData.currentRows,
    selectedEntryId,
    selectedRow,
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
    acceptSelectedSuggestionToExisting,
    acceptSelectedSuggestionAsNew,
    rejectSelectedSuggestion,
  };
};

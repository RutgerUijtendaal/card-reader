import { computed, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { useRoute } from 'vue-router';
import {
  acceptSuggestionAsNew,
  acceptSuggestionToExisting,
  fetchKnownCatalogEntryDetail,
  rejectSuggestion,
} from '@/modules/admin/api/catalog';
import type {
  KeywordRecord,
  SuggestionRecord,
  SymbolRecord,
  TagRecord,
  TypeRecord,
} from '@/modules/admin/types';
import {
  parseAdminCatalogKind,
  parseAdminEntryId,
} from '@/modules/admin/adminRouteState';
import { useAdminRouteSync } from '@/modules/admin/composables/useAdminRouteSync';
import {
  CATALOG_KIND_GROUPS,
  CATALOG_KINDS,
  catalogRowToFormEntry,
  detectionConfigExample,
  isKnownCatalogKind,
  isSuggestedCatalogKind,
  kindItemLabel,
  kindLabel,
  normalizeKnownCatalogDetail,
  referenceAssetsExample,
} from './catalogAdminUtils';
import { extractErrorMessage } from './catalogAdminUtils';
import { useCatalogData } from './useCatalogData';
import { useCatalogEntryActions } from './useCatalogEntryActions';
import { useCatalogEntryForm } from './useCatalogEntryForm';
import { useSymbolAssetUpload } from './useSymbolAssetUpload';

export { detectionConfigExample, kindItemLabel, kindLabel, referenceAssetsExample };

export const useCatalogAdmin = () => {
  const route = useRoute();
  const { replaceAdminQuery } = useAdminRouteSync();
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
  const selectedKnownDetail = ref<KeywordRecord | TagRecord | TypeRecord | SymbolRecord | null>(null);

  const selectedRow = computed(() =>
    selectedEntryId.value
      ? catalogData.allCurrentRows.value.find((row) => row.id === selectedEntryId.value) ?? null
      : null,
  );
  const selectedSuggestionRow = computed(() =>
    selectedRow.value && 'status' in selectedRow.value ? (selectedRow.value as SuggestionRecord) : null,
  );
  const selectedKnownRow = computed(() => {
    if (!selectedRow.value || 'status' in selectedRow.value) {
      return null;
    }
    return selectedKnownDetail.value ?? selectedRow.value;
  });
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
    selectedKnownDetail.value = null;
    resetEditorEntry();
    replaceAdminQuery({
      tab: 'catalog',
      kind: catalogData.selectedKind.value,
      entryId: null,
    });
  };

  const selectEntry = async (entryId: string): Promise<void> => {
    const row = catalogData.allCurrentRows.value.find((item) => item.id === entryId);
    if (!row) return;
    selectedEntryId.value = row.id;
    if ('status' in row) {
      selectedKnownDetail.value = null;
      suggestionExistingTargetId.value = '';
      suggestionNewLabel.value = row.display_value;
      suggestionNewKey.value = '';
      replaceAdminQuery({
        tab: 'catalog',
        kind: catalogData.selectedKind.value,
        entryId: row.id,
      });
      return;
    }
    replaceAdminQuery({
      tab: 'catalog',
      kind: catalogData.selectedKind.value,
      entryId: row.id,
    });
    await loadKnownDetail(row.id);
  };

  const selectKind = (kind: (typeof CATALOG_KINDS)[number]): void => {
    catalogData.selectKind(kind);
    selectedEntryId.value = null;
    selectedKnownDetail.value = null;
    resetEditorEntry();
    replaceAdminQuery({
      tab: 'catalog',
      kind,
      entryId: null,
    });
  };

  watch(
    () => route.query,
    async (query) => {
      const routeKind = parseAdminCatalogKind(query);
      const routeEntryId = parseAdminEntryId(query);

      if (catalogData.selectedKind.value !== routeKind) {
        catalogData.selectKind(routeKind);
      }

      if (!routeEntryId) {
        if (selectedEntryId.value !== null) {
          selectedEntryId.value = null;
          selectedKnownDetail.value = null;
          resetEditorEntry();
        }
        return;
      }

      if (selectedEntryId.value !== routeEntryId) {
        await selectEntry(routeEntryId);
      }
    },
    { immediate: true },
  );

  const loadCatalog = async (): Promise<void> => {
    await catalogData.loadCatalog();
    const routeKind = parseAdminCatalogKind(route.query);
    const routeEntryId = parseAdminEntryId(route.query);

    if (catalogData.selectedKind.value !== routeKind) {
      catalogData.selectKind(routeKind);
    }

    if (!routeEntryId) {
      return;
    }

    if (selectedEntryId.value !== routeEntryId) {
      await selectEntry(routeEntryId);
      return;
    }

    if (selectedEntryId.value && isKnownCatalogKind(catalogData.selectedKind.value)) {
      await loadKnownDetail(selectedEntryId.value);
    }
  };

  const entryActions = useCatalogEntryActions({
    selectedKind: catalogData.selectedKind,
    editorEntry,
    selectedEntryId,
    loadCatalog,
    resetEditorEntry,
  });
  const symbolAssetUpload = useSymbolAssetUpload(editorEntry);

  const reloadSuggestions = async (): Promise<void> => {
    await loadCatalog();
    if (!selectedEntryId.value) {
      return;
    }
    const row = catalogData.allCurrentRows.value.find((item) => item.id === selectedEntryId.value);
    if (row && 'status' in row) {
      suggestionNewLabel.value = row.display_value;
    }
  };

  const loadKnownDetail = async (entryId: string): Promise<void> => {
    const detailKind = catalogData.selectedKind.value;
    if (!isKnownCatalogKind(detailKind)) {
      selectedKnownDetail.value = null;
      return;
    }
    try {
      const detail = await fetchKnownCatalogEntryDetail(detailKind, entryId);
      const normalized = normalizeKnownCatalogDetail(detailKind, detail);
      if (selectedEntryId.value !== entryId || catalogData.selectedKind.value !== detailKind) {
        return;
      }
      selectedKnownDetail.value = normalized;
      setEditorEntry(catalogRowToFormEntry(normalized));
    } catch (error) {
      selectedKnownDetail.value = null;
      toast.error(extractErrorMessage(error, 'Failed to load entry details.'));
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
    loadCatalog,
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

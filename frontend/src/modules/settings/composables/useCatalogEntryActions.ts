import { computed, reactive, ref } from 'vue';
import { toast } from 'vue-sonner';
import {
  createCatalogEntry,
  deleteCatalogEntry,
  updateCatalogEntry,
} from '@/modules/settings/api/catalog';
import type { CatalogFormEntry, CatalogKind, CatalogRow } from '@/modules/settings/types';
import {
  buildCreatePayload,
  catalogFormEntryToRow,
  buildUpdatePayload,
  extractErrorMessage,
} from './catalogSettingsUtils';

type CatalogEntryActionsOptions = {
  selectedKind: { value: CatalogKind };
  editorEntry: CatalogFormEntry;
  selectedEntryId: { value: string | null };
  loadCatalog: () => Promise<void>;
  resetEditorEntry: () => void;
};

export const useCatalogEntryActions = ({
  selectedKind,
  editorEntry,
  selectedEntryId,
  loadCatalog,
  resetEditorEntry,
}: CatalogEntryActionsOptions) => {
  const savingEntryIds = ref<Set<string>>(new Set());
  const deletingEntryIds = ref<Set<string>>(new Set());
  const creatingEntry = ref(false);

  const deleteModal = reactive<{
    open: boolean;
    loading: boolean;
    kind: CatalogKind | null;
    entryId: string | null;
    entryLabel: string;
  }>({
    open: false,
    loading: false,
    kind: null,
    entryId: null,
    entryLabel: '',
  });

  const deleteModalMessage = computed(
    () =>
      `Delete "${deleteModal.entryLabel || 'this entry'}"?\n\nThis also removes existing relations from card versions and cannot be undone.`,
  );

  const createEntry = async (): Promise<void> => {
    if (creatingEntry.value) return;
    if (!editorEntry.label.trim()) {
      toast.error('Label is required.');
      return;
    }

    creatingEntry.value = true;
    const kind = selectedKind.value;

    try {
      await createCatalogEntry(kind, buildCreatePayload(kind, editorEntry));
      toast.success('Entry created.');
      resetEditorEntry();
      await loadCatalog();
    } catch (error) {
      console.error('Create entry failed', error);
      toast.error(extractErrorMessage(error, 'Failed to create entry.'));
    } finally {
      creatingEntry.value = false;
    }
  };

  const updateSelectedEntry = async (): Promise<void> => {
    const entryId = selectedEntryId.value;
    if (!entryId) return;
    const kind = selectedKind.value;
    const entry = catalogFormEntryToRow(kind, entryId, editorEntry);
    const next = new Set(savingEntryIds.value);
    next.add(entry.id);
    savingEntryIds.value = next;

    try {
      await updateCatalogEntry(kind, entry.id, buildUpdatePayload(kind, entry));
      toast.success('Entry updated.');
      await loadCatalog();
    } catch (error) {
      console.error('Update entry failed', error);
      toast.error(extractErrorMessage(error, 'Failed to update entry.'));
    } finally {
      const done = new Set(savingEntryIds.value);
      done.delete(entry.id);
      savingEntryIds.value = done;
    }
  };

  const openDeleteModal = (kind: CatalogKind, entry: CatalogRow): void => {
    if (deletingEntryIds.value.has(entry.id)) return;
    deleteModal.kind = kind;
    deleteModal.entryId = entry.id;
    deleteModal.entryLabel = entry.label?.trim() || entry.key || 'this entry';
    deleteModal.open = true;
  };

  const resetDeleteModal = (): void => {
    deleteModal.open = false;
    deleteModal.loading = false;
    deleteModal.kind = null;
    deleteModal.entryId = null;
    deleteModal.entryLabel = '';
  };

  const closeDeleteModal = (): void => {
    if (deleteModal.loading) return;
    resetDeleteModal();
  };

  const confirmDeleteEntry = async (): Promise<void> => {
    if (!deleteModal.kind || !deleteModal.entryId) return;
    const kind = deleteModal.kind;
    const entryId = deleteModal.entryId;

    const next = new Set(deletingEntryIds.value);
    if (next.has(entryId)) return;
    next.add(entryId);
    deletingEntryIds.value = next;
    deleteModal.loading = true;

    try {
      await deleteCatalogEntry(kind, entryId);
      resetDeleteModal();
      toast.success('Entry deleted.');
      await loadCatalog();
    } catch (error) {
      console.error('Delete entry failed', error);
      toast.error(extractErrorMessage(error, 'Failed to delete entry.'));
    } finally {
      const done = new Set(deletingEntryIds.value);
      done.delete(entryId);
      deletingEntryIds.value = done;
      if (deleteModal.entryId === entryId) {
        deleteModal.loading = false;
      }
    }
  };

  return {
    savingEntryIds,
    deletingEntryIds,
    creatingEntry,
    deleteModal,
    deleteModalMessage,
    createEntry,
    updateSelectedEntry,
    openDeleteModal,
    closeDeleteModal,
    confirmDeleteEntry,
  };
};

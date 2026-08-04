import { reactive } from 'vue';
import type { CatalogFormEntry } from '@/features/admin/types';
import { createEmptyCatalogEntry } from '@/features/admin/utils/catalogAdmin';

export const useCatalogEntryForm = () => {
  const newEntry = reactive<CatalogFormEntry>(createEmptyCatalogEntry());

  const resetNewEntryForm = (): void => {
    Object.assign(newEntry, createEmptyCatalogEntry());
  };

  const setNewEntry = (entry: CatalogFormEntry): void => {
    Object.assign(newEntry, entry);
  };

  return {
    newEntry,
    resetNewEntryForm,
    setNewEntry,
  };
};

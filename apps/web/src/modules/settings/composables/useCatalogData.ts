import { computed, reactive, ref } from 'vue';
import { fetchCatalog } from '@/modules/settings/api/catalog';
import type {
  CatalogFormEntry,
  CatalogKind,
  CatalogRow,
  KeywordRecord,
  SymbolRecord,
  TagRecord,
  TypeRecord,
} from '@/modules/settings/types';

export const useCatalogData = (resetNewEntryForm: () => void) => {
  const selectedKind = ref<CatalogKind>('keywords');
  const catalog = reactive<{
    keywords: KeywordRecord[];
    tags: TagRecord[];
    symbols: SymbolRecord[];
    types: TypeRecord[];
  }>({
    keywords: [],
    tags: [],
    symbols: [],
    types: [],
  });

  const currentRows = computed<CatalogRow[]>(() => catalog[selectedKind.value]);

  const selectKind = (kind: CatalogKind): void => {
    selectedKind.value = kind;
    resetNewEntryForm();
  };

  const loadCatalog = async (): Promise<void> => {
    const data = await fetchCatalog();
    catalog.keywords = data.keywords ?? [];
    catalog.tags = data.tags ?? [];
    catalog.symbols = data.symbols ?? [];
    catalog.types = data.types ?? [];
  };

  const replaceEntry = (kind: CatalogKind, entryId: string, nextEntry: CatalogFormEntry): void => {
    const rows = catalog[kind] as CatalogRow[];
    const index = rows.findIndex((row) => row.id === entryId);
    if (index < 0) return;
    rows[index] = { ...rows[index], ...nextEntry } as CatalogRow;
  };

  return {
    selectedKind,
    catalog,
    currentRows,
    selectKind,
    loadCatalog,
    replaceEntry,
  };
};

import { computed, reactive, ref } from 'vue';
import { fetchCatalog } from '@/modules/settings/api/catalog';
import type {
  CatalogFormEntry,
  CatalogKind,
  CatalogRow,
  CatalogSearchState,
  KeywordRecord,
  SymbolRecord,
  TagRecord,
  TypeRecord,
} from '@/modules/settings/types';

export const useCatalogData = (resetNewEntryForm: () => void) => {
  const selectedKind = ref<CatalogKind>('keywords');
  const searchFilters = reactive<CatalogSearchState>({
    keywords: '',
    tags: '',
    symbols: '',
    types: '',
  });
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

  const currentSearchTerm = computed<string>(() => searchFilters[selectedKind.value]);
  const allCurrentRows = computed<CatalogRow[]>(() => catalog[selectedKind.value]);
  const currentRows = computed<CatalogRow[]>(() => {
    const query = currentSearchTerm.value.trim().toLowerCase();
    if (query.length === 0) {
      return allCurrentRows.value;
    }

    return allCurrentRows.value.filter((row) => matchesCatalogSearch(row, query));
  });

  const selectKind = (kind: CatalogKind): void => {
    selectedKind.value = kind;
    resetNewEntryForm();
  };

  const setSearchTerm = (value: string): void => {
    searchFilters[selectedKind.value] = value;
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
    currentSearchTerm,
    allCurrentRows,
    currentRows,
    selectKind,
    setSearchTerm,
    loadCatalog,
    replaceEntry,
  };
};

const matchesCatalogSearch = (row: CatalogRow, query: string): boolean => {
  const haystacks = [row.label, row.key];

  if ('identifiers_text' in row) {
    haystacks.push(row.identifiers_text);
  }

  if ('symbol_type' in row) {
    haystacks.push(row.symbol_type, row.text_token, row.detector_type);
  }

  return haystacks.some((value) => value.toLowerCase().includes(query));
};

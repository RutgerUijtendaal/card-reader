import { computed, reactive, ref } from 'vue';
import { fetchCatalog } from '@/modules/settings/api/catalog';
import type {
  CatalogKind,
  CatalogRow,
  CatalogSearchState,
  KeywordRecord,
  SuggestionRecord,
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
    'suggested-tags': '',
    'suggested-types': '',
  });
  const catalog = reactive<{
    keywords: KeywordRecord[];
    tags: TagRecord[];
    symbols: SymbolRecord[];
    types: TypeRecord[];
    'suggested-tags': SuggestionRecord[];
    'suggested-types': SuggestionRecord[];
  }>({
    keywords: [],
    tags: [],
    symbols: [],
    types: [],
    'suggested-tags': [],
    'suggested-types': [],
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
    catalog.keywords = data.known.keywords ?? [];
    catalog.tags = data.known.tags ?? [];
    catalog.symbols = data.known.symbols ?? [];
    catalog.types = data.known.types ?? [];
    catalog['suggested-tags'] = data.suggested.tags ?? [];
    catalog['suggested-types'] = data.suggested.types ?? [];
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

  if ('status' in row) {
    haystacks.push(
      row.display_value,
      row.normalized_value,
      row.status,
      row.accepted_target?.label ?? '',
      row.accepted_target?.key ?? '',
      ...row.occurrences.map((item) => `${item.card_label} ${item.source_text}`),
    );
  }

  return haystacks.some((value) => value.toLowerCase().includes(query));
};

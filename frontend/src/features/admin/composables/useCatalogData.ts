import { computed, reactive, ref } from 'vue';
import { fetchCatalog, fetchDeckTagCatalog } from '@/features/admin/api/catalog';
import type {
  CatalogKind,
  CatalogRow,
  CatalogSearchState,
  KeywordRecord,
  SuggestionRecord,
  SymbolRecord,
  TagRecord,
  TypeRecord,
  DeckTagRecord,
  ClassificationDefinitionRecord,
} from '@/features/admin/types';

export const useCatalogData = (resetNewEntryForm: () => void) => {
  let loadGeneration = 0;
  const selectedKind = ref<CatalogKind>('keywords');
  const searchFilters = reactive<CatalogSearchState>({
    keywords: '',
    tags: '',
    symbols: '',
    types: '',
    'suggested-tags': '',
    'suggested-types': '',
    'card-roles': '',
    'card-factions': '',
    'deck-roles': '',
    'deck-types': '',
    'suggested-deck-types': '',
  });
  const catalog = reactive<{
    keywords: KeywordRecord[];
    tags: TagRecord[];
    symbols: SymbolRecord[];
    types: TypeRecord[];
    'suggested-tags': SuggestionRecord[];
    'suggested-types': SuggestionRecord[];
    'card-roles': ClassificationDefinitionRecord[];
    'card-factions': ClassificationDefinitionRecord[];
    'deck-roles': DeckTagRecord[];
    'deck-types': DeckTagRecord[];
    'suggested-deck-types': SuggestionRecord[];
  }>({
    keywords: [],
    tags: [],
    symbols: [],
    types: [],
    'suggested-tags': [],
    'suggested-types': [],
    'card-roles': [],
    'card-factions': [],
    'deck-roles': [],
    'deck-types': [],
    'suggested-deck-types': [],
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
    const generation = ++loadGeneration;
    const [data, deckTagData] = await Promise.all([fetchCatalog(), fetchDeckTagCatalog()]);
    if (generation !== loadGeneration) {
      return;
    }
    catalog.keywords = data.known.keywords ?? [];
    catalog.tags = data.known.tags ?? [];
    catalog.symbols = data.known.symbols ?? [];
    catalog.types = data.known.types ?? [];
    catalog['suggested-tags'] = data.suggested.tags ?? [];
    catalog['suggested-types'] = data.suggested.types ?? [];
    catalog['card-roles'] = data.classification?.roles ?? [];
    catalog['card-factions'] = data.classification?.factions ?? [];
    catalog['deck-roles'] = deckTagData.roles;
    catalog['deck-types'] = deckTagData.types;
    catalog['suggested-deck-types'] = deckTagData.suggestedTypes;
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
      ...(row.linked_decks ?? []).map((deck) => `${deck.name} ${deck.owner.username}`),
    );
  }

  return haystacks.some((value) => value.toLowerCase().includes(query));
};

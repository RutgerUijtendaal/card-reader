import { computed, reactive, ref } from 'vue';
import { fetchCatalog, fetchDeckTagCatalog } from '@/features/admin/api/catalog';
import type {
  CatalogKind,
  CatalogRow,
  CatalogSearchState,
  KeywordRecord,
  SuggestionStatus,
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
    'card-mana-families': '',
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
    'card-mana-families': ClassificationDefinitionRecord[];
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
    'card-mana-families': [],
    'deck-roles': [],
    'deck-types': [],
    'suggested-deck-types': [],
  });

  const currentSearchTerm = computed<string>(() => searchFilters[selectedKind.value]);
  const allCurrentRows = computed<CatalogRow[]>(() => catalog[selectedKind.value]);
  const currentRows = computed<CatalogRow[]>(() => {
    const query = currentSearchTerm.value.trim().toLowerCase();
    const matchingRows = query.length === 0
      ? allCurrentRows.value
      : allCurrentRows.value.filter((row) => matchesCatalogSearch(row, query));

    return selectedKind.value === 'suggested-tags'
      ? sortSuggestedTagsByStatus(matchingRows)
      : matchingRows;
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
    catalog['card-mana-families'] = data.classification?.mana_families ?? [];
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

const SUGGESTION_STATUS_ORDER: Record<SuggestionStatus, number> = {
  pending: 0,
  accepted: 1,
  rejected: 2,
};

const sortSuggestedTagsByStatus = (rows: CatalogRow[]): CatalogRow[] =>
  [...rows].sort((left, right) => {
    if (!('status' in left) || !('status' in right)) {
      return 0;
    }

    const statusComparison = SUGGESTION_STATUS_ORDER[left.status]
      - SUGGESTION_STATUS_ORDER[right.status];
    if (statusComparison !== 0) {
      return statusComparison;
    }

    return left.label.localeCompare(right.label);
  });

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

import type { LocationQuery, LocationQueryRaw, LocationQueryValue } from 'vue-router';
import type {
  CardFiltersResponse,
  MetadataOption,
  SymbolFilterOption,
} from '@/modules/card-detail/types';

export type CardFilterState = {
  query: string;
  manaCost: string;
  templateId: string;
  attackMin: string;
  attackMax: string;
  healthMin: string;
  healthMax: string;
  keywordKeys: string[];
  tagKeys: string[];
  manaSymbolKeys: string[];
  affinitySymbolKeys: string[];
  devotionSymbolKeys: string[];
  otherSymbolKeys: string[];
  typeKeys: string[];
};

export type CardFilterSelectionState = {
  query: string;
  manaCost: string;
  templateId: string;
  attackMin: string;
  attackMax: string;
  healthMin: string;
  healthMax: string;
  keywordIds: string[];
  tagIds: string[];
  manaTypeSymbolIds: string[];
  affinitySymbolIds: string[];
  devotionSymbolIds: string[];
  otherSymbolIds: string[];
  typeIds: string[];
};

export type CardFilterCatalog = {
  keywords: MetadataOption[];
  tags: MetadataOption[];
  types: MetadataOption[];
  manaSymbols: SymbolFilterOption[];
  affinitySymbols: SymbolFilterOption[];
  devotionSymbols: SymbolFilterOption[];
  otherSymbols: SymbolFilterOption[];
};

export const createEmptyCardFilterState = (): CardFilterState => ({
  query: '',
  manaCost: '',
  templateId: '',
  attackMin: '',
  attackMax: '',
  healthMin: '',
  healthMax: '',
  keywordKeys: [],
  tagKeys: [],
  manaSymbolKeys: [],
  affinitySymbolKeys: [],
  devotionSymbolKeys: [],
  otherSymbolKeys: [],
  typeKeys: [],
});

export const createEmptyCardFilterSelectionState = (): CardFilterSelectionState => ({
  query: '',
  manaCost: '',
  templateId: '',
  attackMin: '',
  attackMax: '',
  healthMin: '',
  healthMax: '',
  keywordIds: [],
  tagIds: [],
  manaTypeSymbolIds: [],
  affinitySymbolIds: [],
  devotionSymbolIds: [],
  otherSymbolIds: [],
  typeIds: [],
});

const normalizeStringValue = (value: string | null | undefined): string => value?.trim() ?? '';

const normalizeStringArray = (values: readonly string[]): string[] =>
  [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((left, right) =>
    left.localeCompare(right),
  );

const readQueryValues = (
  value: LocationQueryValue | LocationQueryValue[] | readonly LocationQueryValue[] | null | undefined,
): string[] => {
  if (Array.isArray(value)) {
    return value.filter((entry): entry is string => typeof entry === 'string');
  }
  return typeof value === 'string' ? [value] : [];
};

export const normalizeCardFilterState = (state: CardFilterState): CardFilterState => ({
  query: normalizeStringValue(state.query),
  manaCost: normalizeStringValue(state.manaCost),
  templateId: normalizeStringValue(state.templateId),
  attackMin: normalizeStringValue(state.attackMin),
  attackMax: normalizeStringValue(state.attackMax),
  healthMin: normalizeStringValue(state.healthMin),
  healthMax: normalizeStringValue(state.healthMax),
  keywordKeys: normalizeStringArray(state.keywordKeys),
  tagKeys: normalizeStringArray(state.tagKeys),
  manaSymbolKeys: normalizeStringArray(state.manaSymbolKeys),
  affinitySymbolKeys: normalizeStringArray(state.affinitySymbolKeys),
  devotionSymbolKeys: normalizeStringArray(state.devotionSymbolKeys),
  otherSymbolKeys: normalizeStringArray(state.otherSymbolKeys),
  typeKeys: normalizeStringArray(state.typeKeys),
});

export const normalizeCardFilterSelectionState = (
  state: CardFilterSelectionState,
): CardFilterSelectionState => ({
  query: normalizeStringValue(state.query),
  manaCost: normalizeStringValue(state.manaCost),
  templateId: normalizeStringValue(state.templateId),
  attackMin: normalizeStringValue(state.attackMin),
  attackMax: normalizeStringValue(state.attackMax),
  healthMin: normalizeStringValue(state.healthMin),
  healthMax: normalizeStringValue(state.healthMax),
  keywordIds: normalizeStringArray(state.keywordIds),
  tagIds: normalizeStringArray(state.tagIds),
  manaTypeSymbolIds: normalizeStringArray(state.manaTypeSymbolIds),
  affinitySymbolIds: normalizeStringArray(state.affinitySymbolIds),
  devotionSymbolIds: normalizeStringArray(state.devotionSymbolIds),
  otherSymbolIds: normalizeStringArray(state.otherSymbolIds),
  typeIds: normalizeStringArray(state.typeIds),
});

export const parseCardFilterRouteQuery = (query: LocationQuery): CardFilterState =>
  normalizeCardFilterState({
    query: typeof query.q === 'string' ? query.q : '',
    manaCost: typeof query.mana_cost === 'string' ? query.mana_cost : '',
    templateId: typeof query.template_id === 'string' ? query.template_id : '',
    attackMin: typeof query.attack_min === 'string' ? query.attack_min : '',
    attackMax: typeof query.attack_max === 'string' ? query.attack_max : '',
    healthMin: typeof query.health_min === 'string' ? query.health_min : '',
    healthMax: typeof query.health_max === 'string' ? query.health_max : '',
    keywordKeys: readQueryValues(query.keyword_keys),
    tagKeys: readQueryValues(query.tag_keys),
    manaSymbolKeys: readQueryValues(query.mana_symbol_keys),
    affinitySymbolKeys: readQueryValues(query.affinity_symbol_keys),
    devotionSymbolKeys: readQueryValues(query.devotion_symbol_keys),
    otherSymbolKeys: readQueryValues(query.other_symbol_keys),
    typeKeys: readQueryValues(query.type_keys),
  });

export const buildCardFilterRouteQuery = (state: CardFilterState): LocationQueryRaw => {
  const normalized = normalizeCardFilterState(state);
  const query: LocationQueryRaw = {};

  if (normalized.query) query.q = normalized.query;
  if (normalized.manaCost) query.mana_cost = normalized.manaCost;
  if (normalized.templateId) query.template_id = normalized.templateId;
  if (normalized.attackMin) query.attack_min = normalized.attackMin;
  if (normalized.attackMax) query.attack_max = normalized.attackMax;
  if (normalized.healthMin) query.health_min = normalized.healthMin;
  if (normalized.healthMax) query.health_max = normalized.healthMax;
  if (normalized.keywordKeys.length > 0) query.keyword_keys = normalized.keywordKeys;
  if (normalized.tagKeys.length > 0) query.tag_keys = normalized.tagKeys;
  if (normalized.manaSymbolKeys.length > 0) query.mana_symbol_keys = normalized.manaSymbolKeys;
  if (normalized.affinitySymbolKeys.length > 0) query.affinity_symbol_keys = normalized.affinitySymbolKeys;
  if (normalized.devotionSymbolKeys.length > 0) query.devotion_symbol_keys = normalized.devotionSymbolKeys;
  if (normalized.otherSymbolKeys.length > 0) query.other_symbol_keys = normalized.otherSymbolKeys;
  if (normalized.typeKeys.length > 0) query.type_keys = normalized.typeKeys;

  return query;
};

export const buildCardFilterRouteSearchParams = (state: CardFilterState): URLSearchParams => {
  const params = new URLSearchParams();
  const query = buildCardFilterRouteQuery(state);

  Object.entries(query).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((entry) => params.append(key, String(entry)));
      return;
    }
    if (value !== undefined) {
      params.set(key, String(value));
    }
  });

  return params;
};

export const getCardFilterSignature = (state: CardFilterState): string =>
  buildCardFilterRouteSearchParams(state).toString();

export const sameCardFilterState = (left: CardFilterState, right: CardFilterState): boolean =>
  getCardFilterSignature(left) === getCardFilterSignature(right);

export const createCardFilterCatalog = (filters: CardFiltersResponse): CardFilterCatalog => ({
  keywords: filters.keywords ?? [],
  tags: filters.tags ?? [],
  types: filters.types ?? [],
  manaSymbols: (filters.symbols ?? []).filter((row) => row.symbol_type === 'mana'),
  affinitySymbols: (filters.symbols ?? []).filter((row) => row.symbol_type === 'affinity'),
  devotionSymbols: (filters.symbols ?? []).filter((row) => row.symbol_type === 'devotion'),
  otherSymbols: (filters.symbols ?? []).filter(
    (row) => !['mana', 'devotion', 'affinity'].includes(row.symbol_type),
  ),
});

const resolveIdsFromKeys = (keys: string[], options: MetadataOption[]): string[] => {
  const idByKey = new Map(options.map((option) => [option.key, option.id]));
  return keys.map((key) => idByKey.get(key)).filter((id): id is string => typeof id === 'string');
};

const resolveKeysFromIds = (ids: string[], options: MetadataOption[]): string[] => {
  const keyById = new Map(options.map((option) => [option.id, option.key]));
  return ids.map((id) => keyById.get(id)).filter((key): key is string => typeof key === 'string');
};

export const buildCardFilterSelectionState = (
  state: CardFilterState,
  catalog: CardFilterCatalog,
): CardFilterSelectionState =>
  normalizeCardFilterSelectionState({
    query: state.query,
    manaCost: state.manaCost,
    templateId: state.templateId,
    attackMin: state.attackMin,
    attackMax: state.attackMax,
    healthMin: state.healthMin,
    healthMax: state.healthMax,
    keywordIds: resolveIdsFromKeys(state.keywordKeys, catalog.keywords),
    tagIds: resolveIdsFromKeys(state.tagKeys, catalog.tags),
    manaTypeSymbolIds: resolveIdsFromKeys(state.manaSymbolKeys, catalog.manaSymbols),
    affinitySymbolIds: resolveIdsFromKeys(state.affinitySymbolKeys, catalog.affinitySymbols),
    devotionSymbolIds: resolveIdsFromKeys(state.devotionSymbolKeys, catalog.devotionSymbols),
    otherSymbolIds: resolveIdsFromKeys(state.otherSymbolKeys, catalog.otherSymbols),
    typeIds: resolveIdsFromKeys(state.typeKeys, catalog.types),
  });

export const buildCardFilterStateFromSelection = (
  state: CardFilterSelectionState,
  catalog: CardFilterCatalog,
): CardFilterState =>
  normalizeCardFilterState({
    query: state.query,
    manaCost: state.manaCost,
    templateId: state.templateId,
    attackMin: state.attackMin,
    attackMax: state.attackMax,
    healthMin: state.healthMin,
    healthMax: state.healthMax,
    keywordKeys: resolveKeysFromIds(state.keywordIds, catalog.keywords),
    tagKeys: resolveKeysFromIds(state.tagIds, catalog.tags),
    manaSymbolKeys: resolveKeysFromIds(state.manaTypeSymbolIds, catalog.manaSymbols),
    affinitySymbolKeys: resolveKeysFromIds(state.affinitySymbolIds, catalog.affinitySymbols),
    devotionSymbolKeys: resolveKeysFromIds(state.devotionSymbolIds, catalog.devotionSymbols),
    otherSymbolKeys: resolveKeysFromIds(state.otherSymbolIds, catalog.otherSymbols),
    typeKeys: resolveKeysFromIds(state.typeIds, catalog.types),
  });

export const buildCardFilterApiSearchParams = (
  state: CardFilterSelectionState,
): URLSearchParams => {
  const normalized = normalizeCardFilterSelectionState(state);
  const params = new URLSearchParams();

  if (normalized.query) params.set('q', normalized.query);
  if (normalized.manaCost) params.set('mana_cost', normalized.manaCost);
  if (normalized.templateId) params.set('template_id', normalized.templateId);
  if (normalized.attackMin) params.set('attack_min', normalized.attackMin);
  if (normalized.attackMax) params.set('attack_max', normalized.attackMax);
  if (normalized.healthMin) params.set('health_min', normalized.healthMin);
  if (normalized.healthMax) params.set('health_max', normalized.healthMax);

  normalized.keywordIds.forEach((id) => params.append('keyword_ids', id));
  normalized.tagIds.forEach((id) => params.append('tag_ids', id));
  [
    ...normalized.manaTypeSymbolIds,
    ...normalized.affinitySymbolIds,
    ...normalized.devotionSymbolIds,
    ...normalized.otherSymbolIds,
  ]
    .sort((left, right) => left.localeCompare(right))
    .forEach((id) => params.append('symbol_ids', id));
  normalized.typeIds.forEach((id) => params.append('type_ids', id));

  return params;
};

import type { LocationQuery, LocationQueryRaw, LocationQueryValue } from 'vue-router';
import type {
  CardFiltersResponse,
  MetadataOption,
  SymbolFilterOption,
} from '@/modules/card-detail/types';

export type CardFilterState = {
  query: string;
  lifecycleStatus?: CardLifecycleFilterValue;
  keywordMatch: 'any' | 'all';
  tagMatch: 'any' | 'all';
  typeMatch: 'any' | 'all';
  manaSymbolMatch: 'any' | 'all';
  affinitySymbolMatch: 'any' | 'all';
  devotionSymbolMatch: 'any' | 'all';
  otherSymbolMatch: 'any' | 'all';
  templateId: string;
  manaCostMin: string;
  manaCostMax: string;
  attackMin: string;
  attackMax: string;
  healthMin: string;
  healthMax: string;
  keywordKeys: string[];
  tagKeys: string[];
  manaSymbolKeys: string[];
  manaSymbolExcludeKeys: string[];
  affinitySymbolKeys: string[];
  affinitySymbolExcludeKeys: string[];
  devotionSymbolKeys: string[];
  devotionSymbolExcludeKeys: string[];
  otherSymbolKeys: string[];
  otherSymbolExcludeKeys: string[];
  typeKeys: string[];
};

export type CardFilterSelectionState = {
  query: string;
  lifecycleStatus?: CardLifecycleFilterValue;
  keywordMatch: 'any' | 'all';
  tagMatch: 'any' | 'all';
  typeMatch: 'any' | 'all';
  manaSymbolMatch: 'any' | 'all';
  affinitySymbolMatch: 'any' | 'all';
  devotionSymbolMatch: 'any' | 'all';
  otherSymbolMatch: 'any' | 'all';
  templateId: string;
  manaCostMin: string;
  manaCostMax: string;
  attackMin: string;
  attackMax: string;
  healthMin: string;
  healthMax: string;
  keywordIds: string[];
  tagIds: string[];
  manaTypeSymbolIds: string[];
  manaTypeSymbolExcludeIds: string[];
  affinitySymbolIds: string[];
  affinitySymbolExcludeIds: string[];
  devotionSymbolIds: string[];
  devotionSymbolExcludeIds: string[];
  otherSymbolIds: string[];
  otherSymbolExcludeIds: string[];
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

export type CardFilterApiPayload = {
  q?: string;
  lifecycle_status?: CardLifecycleFilterValue;
  keyword_ids?: string[];
  keyword_match?: 'any' | 'all';
  tag_ids?: string[];
  tag_match?: 'any' | 'all';
  type_ids?: string[];
  type_match?: 'any' | 'all';
  mana_symbol_ids?: string[];
  mana_symbol_exclude_ids?: string[];
  mana_symbol_match?: 'any' | 'all';
  affinity_symbol_ids?: string[];
  affinity_symbol_exclude_ids?: string[];
  affinity_symbol_match?: 'any' | 'all';
  devotion_symbol_ids?: string[];
  devotion_symbol_exclude_ids?: string[];
  devotion_symbol_match?: 'any' | 'all';
  other_symbol_ids?: string[];
  other_symbol_exclude_ids?: string[];
  other_symbol_match?: 'any' | 'all';
  template_id?: string;
  mana_cost_min?: string;
  mana_cost_max?: string;
  attack_min?: string;
  attack_max?: string;
  health_min?: string;
  health_max?: string;
};

export type CardLifecycleStatus = 'active' | 'deprecated';
export type CardLifecycleFilterValue = CardLifecycleStatus | 'all';

export const createEmptyCardFilterState = (): CardFilterState => ({
  query: '',
  lifecycleStatus: 'active',
  keywordMatch: 'any',
  tagMatch: 'any',
  typeMatch: 'any',
  manaSymbolMatch: 'any',
  affinitySymbolMatch: 'any',
  devotionSymbolMatch: 'any',
  otherSymbolMatch: 'any',
  templateId: '',
  manaCostMin: '',
  manaCostMax: '',
  attackMin: '',
  attackMax: '',
  healthMin: '',
  healthMax: '',
  keywordKeys: [],
  tagKeys: [],
  manaSymbolKeys: [],
  manaSymbolExcludeKeys: [],
  affinitySymbolKeys: [],
  affinitySymbolExcludeKeys: [],
  devotionSymbolKeys: [],
  devotionSymbolExcludeKeys: [],
  otherSymbolKeys: [],
  otherSymbolExcludeKeys: [],
  typeKeys: [],
});

export const createEmptyCardFilterSelectionState = (): CardFilterSelectionState => ({
  query: '',
  lifecycleStatus: 'active',
  keywordMatch: 'any',
  tagMatch: 'any',
  typeMatch: 'any',
  manaSymbolMatch: 'any',
  affinitySymbolMatch: 'any',
  devotionSymbolMatch: 'any',
  otherSymbolMatch: 'any',
  templateId: '',
  manaCostMin: '',
  manaCostMax: '',
  attackMin: '',
  attackMax: '',
  healthMin: '',
  healthMax: '',
  keywordIds: [],
  tagIds: [],
  manaTypeSymbolIds: [],
  manaTypeSymbolExcludeIds: [],
  affinitySymbolIds: [],
  affinitySymbolExcludeIds: [],
  devotionSymbolIds: [],
  devotionSymbolExcludeIds: [],
  otherSymbolIds: [],
  otherSymbolExcludeIds: [],
  typeIds: [],
});

const normalizeStringValue = (value: string | number | null | undefined): string => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(value) : '';
  }
  return value?.trim() ?? '';
};

const normalizeStringArray = (values: readonly string[]): string[] =>
  [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((left, right) =>
    left.localeCompare(right),
  );

const normalizeLifecycleStatus = (value: string | undefined): CardLifecycleFilterValue =>
  value === 'deprecated' || value === 'all' ? value : 'active';

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
  lifecycleStatus: normalizeLifecycleStatus(state.lifecycleStatus),
  keywordMatch: state.keywordMatch === 'all' ? 'all' : 'any',
  tagMatch: state.tagMatch === 'all' ? 'all' : 'any',
  typeMatch: state.typeMatch === 'all' ? 'all' : 'any',
  manaSymbolMatch: state.manaSymbolMatch === 'all' ? 'all' : 'any',
  affinitySymbolMatch: state.affinitySymbolMatch === 'all' ? 'all' : 'any',
  devotionSymbolMatch: state.devotionSymbolMatch === 'all' ? 'all' : 'any',
  otherSymbolMatch: state.otherSymbolMatch === 'all' ? 'all' : 'any',
  templateId: normalizeStringValue(state.templateId),
  manaCostMin: normalizeStringValue(state.manaCostMin),
  manaCostMax: normalizeStringValue(state.manaCostMax),
  attackMin: normalizeStringValue(state.attackMin),
  attackMax: normalizeStringValue(state.attackMax),
  healthMin: normalizeStringValue(state.healthMin),
  healthMax: normalizeStringValue(state.healthMax),
  keywordKeys: normalizeStringArray(state.keywordKeys),
  tagKeys: normalizeStringArray(state.tagKeys),
  manaSymbolKeys: normalizeStringArray(state.manaSymbolKeys),
  manaSymbolExcludeKeys: normalizeStringArray(state.manaSymbolExcludeKeys),
  affinitySymbolKeys: normalizeStringArray(state.affinitySymbolKeys),
  affinitySymbolExcludeKeys: normalizeStringArray(state.affinitySymbolExcludeKeys),
  devotionSymbolKeys: normalizeStringArray(state.devotionSymbolKeys),
  devotionSymbolExcludeKeys: normalizeStringArray(state.devotionSymbolExcludeKeys),
  otherSymbolKeys: normalizeStringArray(state.otherSymbolKeys),
  otherSymbolExcludeKeys: normalizeStringArray(state.otherSymbolExcludeKeys),
  typeKeys: normalizeStringArray(state.typeKeys),
});

export const normalizeCardFilterSelectionState = (
  state: CardFilterSelectionState,
): CardFilterSelectionState => ({
  query: normalizeStringValue(state.query),
  lifecycleStatus: normalizeLifecycleStatus(state.lifecycleStatus),
  keywordMatch: state.keywordMatch === 'all' ? 'all' : 'any',
  tagMatch: state.tagMatch === 'all' ? 'all' : 'any',
  typeMatch: state.typeMatch === 'all' ? 'all' : 'any',
  manaSymbolMatch: state.manaSymbolMatch === 'all' ? 'all' : 'any',
  affinitySymbolMatch: state.affinitySymbolMatch === 'all' ? 'all' : 'any',
  devotionSymbolMatch: state.devotionSymbolMatch === 'all' ? 'all' : 'any',
  otherSymbolMatch: state.otherSymbolMatch === 'all' ? 'all' : 'any',
  templateId: normalizeStringValue(state.templateId),
  manaCostMin: normalizeStringValue(state.manaCostMin),
  manaCostMax: normalizeStringValue(state.manaCostMax),
  attackMin: normalizeStringValue(state.attackMin),
  attackMax: normalizeStringValue(state.attackMax),
  healthMin: normalizeStringValue(state.healthMin),
  healthMax: normalizeStringValue(state.healthMax),
  keywordIds: normalizeStringArray(state.keywordIds),
  tagIds: normalizeStringArray(state.tagIds),
  manaTypeSymbolIds: normalizeStringArray(state.manaTypeSymbolIds),
  manaTypeSymbolExcludeIds: normalizeStringArray(state.manaTypeSymbolExcludeIds),
  affinitySymbolIds: normalizeStringArray(state.affinitySymbolIds),
  affinitySymbolExcludeIds: normalizeStringArray(state.affinitySymbolExcludeIds),
  devotionSymbolIds: normalizeStringArray(state.devotionSymbolIds),
  devotionSymbolExcludeIds: normalizeStringArray(state.devotionSymbolExcludeIds),
  otherSymbolIds: normalizeStringArray(state.otherSymbolIds),
  otherSymbolExcludeIds: normalizeStringArray(state.otherSymbolExcludeIds),
  typeIds: normalizeStringArray(state.typeIds),
});

export const parseCardFilterRouteQuery = (query: LocationQuery): CardFilterState =>
  normalizeCardFilterState({
    query: typeof query.q === 'string' ? query.q : '',
    lifecycleStatus: normalizeLifecycleStatus(
      typeof query.lifecycle_status === 'string' ? query.lifecycle_status : undefined,
    ),
    keywordMatch: query.keyword_match === 'all' ? 'all' : 'any',
    tagMatch: query.tag_match === 'all' ? 'all' : 'any',
    typeMatch: query.type_match === 'all' ? 'all' : 'any',
    manaSymbolMatch: query.mana_symbol_match === 'all' ? 'all' : 'any',
    affinitySymbolMatch: query.affinity_symbol_match === 'all' ? 'all' : 'any',
    devotionSymbolMatch: query.devotion_symbol_match === 'all' ? 'all' : 'any',
    otherSymbolMatch: query.other_symbol_match === 'all' ? 'all' : 'any',
    templateId: typeof query.template_id === 'string' ? query.template_id : '',
    manaCostMin: typeof query.mana_cost_min === 'string' ? query.mana_cost_min : '',
    manaCostMax: typeof query.mana_cost_max === 'string' ? query.mana_cost_max : '',
    attackMin: typeof query.attack_min === 'string' ? query.attack_min : '',
    attackMax: typeof query.attack_max === 'string' ? query.attack_max : '',
    healthMin: typeof query.health_min === 'string' ? query.health_min : '',
    healthMax: typeof query.health_max === 'string' ? query.health_max : '',
    keywordKeys: readQueryValues(query.keyword_keys),
    tagKeys: readQueryValues(query.tag_keys),
    manaSymbolKeys: readQueryValues(query.mana_symbol_keys),
    manaSymbolExcludeKeys: readQueryValues(query.mana_symbol_exclude_keys),
    affinitySymbolKeys: readQueryValues(query.affinity_symbol_keys),
    affinitySymbolExcludeKeys: readQueryValues(query.affinity_symbol_exclude_keys),
    devotionSymbolKeys: readQueryValues(query.devotion_symbol_keys),
    devotionSymbolExcludeKeys: readQueryValues(query.devotion_symbol_exclude_keys),
    otherSymbolKeys: readQueryValues(query.other_symbol_keys),
    otherSymbolExcludeKeys: readQueryValues(query.other_symbol_exclude_keys),
    typeKeys: readQueryValues(query.type_keys),
  });

export const buildCardFilterRouteQuery = (state: CardFilterState): LocationQueryRaw => {
  const normalized = normalizeCardFilterState(state);
  const query: LocationQueryRaw = {};

  if (normalized.query) query.q = normalized.query;
  if (normalized.lifecycleStatus !== 'active') query.lifecycle_status = normalized.lifecycleStatus;
  if (normalized.keywordMatch === 'all') query.keyword_match = 'all';
  if (normalized.tagMatch === 'all') query.tag_match = 'all';
  if (normalized.typeMatch === 'all') query.type_match = 'all';
  if (normalized.manaSymbolMatch === 'all') query.mana_symbol_match = 'all';
  if (normalized.affinitySymbolMatch === 'all') query.affinity_symbol_match = 'all';
  if (normalized.devotionSymbolMatch === 'all') query.devotion_symbol_match = 'all';
  if (normalized.otherSymbolMatch === 'all') query.other_symbol_match = 'all';
  if (normalized.templateId) query.template_id = normalized.templateId;
  if (normalized.manaCostMin) query.mana_cost_min = normalized.manaCostMin;
  if (normalized.manaCostMax) query.mana_cost_max = normalized.manaCostMax;
  if (normalized.attackMin) query.attack_min = normalized.attackMin;
  if (normalized.attackMax) query.attack_max = normalized.attackMax;
  if (normalized.healthMin) query.health_min = normalized.healthMin;
  if (normalized.healthMax) query.health_max = normalized.healthMax;
  if (normalized.keywordKeys.length > 0) query.keyword_keys = normalized.keywordKeys;
  if (normalized.tagKeys.length > 0) query.tag_keys = normalized.tagKeys;
  if (normalized.manaSymbolKeys.length > 0) query.mana_symbol_keys = normalized.manaSymbolKeys;
  if (normalized.manaSymbolExcludeKeys.length > 0) query.mana_symbol_exclude_keys = normalized.manaSymbolExcludeKeys;
  if (normalized.affinitySymbolKeys.length > 0) query.affinity_symbol_keys = normalized.affinitySymbolKeys;
  if (normalized.affinitySymbolExcludeKeys.length > 0) {
    query.affinity_symbol_exclude_keys = normalized.affinitySymbolExcludeKeys;
  }
  if (normalized.devotionSymbolKeys.length > 0) query.devotion_symbol_keys = normalized.devotionSymbolKeys;
  if (normalized.devotionSymbolExcludeKeys.length > 0) {
    query.devotion_symbol_exclude_keys = normalized.devotionSymbolExcludeKeys;
  }
  if (normalized.otherSymbolKeys.length > 0) query.other_symbol_keys = normalized.otherSymbolKeys;
  if (normalized.otherSymbolExcludeKeys.length > 0) query.other_symbol_exclude_keys = normalized.otherSymbolExcludeKeys;
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
  manaSymbols: (filters.symbols ?? []).filter(
    (row) => row.symbol_type === 'mana' && !row.key.startsWith('colorless-mana-'),
  ),
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
    lifecycleStatus: state.lifecycleStatus,
    keywordMatch: state.keywordMatch,
    tagMatch: state.tagMatch,
    typeMatch: state.typeMatch,
    manaSymbolMatch: state.manaSymbolMatch,
    affinitySymbolMatch: state.affinitySymbolMatch,
    devotionSymbolMatch: state.devotionSymbolMatch,
    otherSymbolMatch: state.otherSymbolMatch,
    templateId: state.templateId,
    manaCostMin: state.manaCostMin,
    manaCostMax: state.manaCostMax,
    attackMin: state.attackMin,
    attackMax: state.attackMax,
    healthMin: state.healthMin,
    healthMax: state.healthMax,
    keywordIds: resolveIdsFromKeys(state.keywordKeys, catalog.keywords),
    tagIds: resolveIdsFromKeys(state.tagKeys, catalog.tags),
    manaTypeSymbolIds: resolveIdsFromKeys(state.manaSymbolKeys, catalog.manaSymbols),
    manaTypeSymbolExcludeIds: resolveIdsFromKeys(state.manaSymbolExcludeKeys, catalog.manaSymbols),
    affinitySymbolIds: resolveIdsFromKeys(state.affinitySymbolKeys, catalog.affinitySymbols),
    affinitySymbolExcludeIds: resolveIdsFromKeys(state.affinitySymbolExcludeKeys, catalog.affinitySymbols),
    devotionSymbolIds: resolveIdsFromKeys(state.devotionSymbolKeys, catalog.devotionSymbols),
    devotionSymbolExcludeIds: resolveIdsFromKeys(state.devotionSymbolExcludeKeys, catalog.devotionSymbols),
    otherSymbolIds: resolveIdsFromKeys(state.otherSymbolKeys, catalog.otherSymbols),
    otherSymbolExcludeIds: resolveIdsFromKeys(state.otherSymbolExcludeKeys, catalog.otherSymbols),
    typeIds: resolveIdsFromKeys(state.typeKeys, catalog.types),
  });

export const buildCardFilterStateFromSelection = (
  state: CardFilterSelectionState,
  catalog: CardFilterCatalog,
): CardFilterState =>
  normalizeCardFilterState({
    query: state.query,
    lifecycleStatus: state.lifecycleStatus,
    keywordMatch: state.keywordMatch,
    tagMatch: state.tagMatch,
    typeMatch: state.typeMatch,
    manaSymbolMatch: state.manaSymbolMatch,
    affinitySymbolMatch: state.affinitySymbolMatch,
    devotionSymbolMatch: state.devotionSymbolMatch,
    otherSymbolMatch: state.otherSymbolMatch,
    templateId: state.templateId,
    manaCostMin: state.manaCostMin,
    manaCostMax: state.manaCostMax,
    attackMin: state.attackMin,
    attackMax: state.attackMax,
    healthMin: state.healthMin,
    healthMax: state.healthMax,
    keywordKeys: resolveKeysFromIds(state.keywordIds, catalog.keywords),
    tagKeys: resolveKeysFromIds(state.tagIds, catalog.tags),
    manaSymbolKeys: resolveKeysFromIds(state.manaTypeSymbolIds, catalog.manaSymbols),
    manaSymbolExcludeKeys: resolveKeysFromIds(state.manaTypeSymbolExcludeIds, catalog.manaSymbols),
    affinitySymbolKeys: resolveKeysFromIds(state.affinitySymbolIds, catalog.affinitySymbols),
    affinitySymbolExcludeKeys: resolveKeysFromIds(state.affinitySymbolExcludeIds, catalog.affinitySymbols),
    devotionSymbolKeys: resolveKeysFromIds(state.devotionSymbolIds, catalog.devotionSymbols),
    devotionSymbolExcludeKeys: resolveKeysFromIds(state.devotionSymbolExcludeIds, catalog.devotionSymbols),
    otherSymbolKeys: resolveKeysFromIds(state.otherSymbolIds, catalog.otherSymbols),
    otherSymbolExcludeKeys: resolveKeysFromIds(state.otherSymbolExcludeIds, catalog.otherSymbols),
    typeKeys: resolveKeysFromIds(state.typeIds, catalog.types),
  });

export const buildCardFilterApiSearchParams = (
  state: CardFilterSelectionState,
): URLSearchParams => {
  const payload = buildCardFilterApiPayload(state);
  const normalized = normalizeCardFilterSelectionState(state);
  const params = new URLSearchParams();

  if (payload.q) params.set('q', payload.q);
  if (payload.lifecycle_status) params.set('lifecycle_status', payload.lifecycle_status);
  if (payload.keyword_ids) {
    payload.keyword_ids.forEach((id) => params.append('keyword_ids', id));
    params.set('keyword_match', payload.keyword_match ?? normalized.keywordMatch);
  }
  if (payload.tag_ids) {
    payload.tag_ids.forEach((id) => params.append('tag_ids', id));
    params.set('tag_match', payload.tag_match ?? normalized.tagMatch);
  }
  if (payload.type_ids) {
    payload.type_ids.forEach((id) => params.append('type_ids', id));
    params.set('type_match', payload.type_match ?? normalized.typeMatch);
  }
  if (payload.mana_symbol_ids) {
    payload.mana_symbol_ids.forEach((id) => params.append('mana_symbol_ids', id));
    params.set('mana_symbol_match', payload.mana_symbol_match ?? normalized.manaSymbolMatch);
  }
  if (payload.mana_symbol_exclude_ids) {
    payload.mana_symbol_exclude_ids.forEach((id) => params.append('mana_symbol_exclude_ids', id));
  }
  if (payload.affinity_symbol_ids) {
    payload.affinity_symbol_ids.forEach((id) => params.append('affinity_symbol_ids', id));
    params.set('affinity_symbol_match', payload.affinity_symbol_match ?? normalized.affinitySymbolMatch);
  }
  if (payload.affinity_symbol_exclude_ids) {
    payload.affinity_symbol_exclude_ids.forEach((id) => params.append('affinity_symbol_exclude_ids', id));
  }
  if (payload.devotion_symbol_ids) {
    payload.devotion_symbol_ids.forEach((id) => params.append('devotion_symbol_ids', id));
    params.set('devotion_symbol_match', payload.devotion_symbol_match ?? normalized.devotionSymbolMatch);
  }
  if (payload.devotion_symbol_exclude_ids) {
    payload.devotion_symbol_exclude_ids.forEach((id) => params.append('devotion_symbol_exclude_ids', id));
  }
  if (payload.other_symbol_ids) {
    payload.other_symbol_ids.forEach((id) => params.append('other_symbol_ids', id));
    params.set('other_symbol_match', payload.other_symbol_match ?? normalized.otherSymbolMatch);
  }
  if (payload.other_symbol_exclude_ids) {
    payload.other_symbol_exclude_ids.forEach((id) => params.append('other_symbol_exclude_ids', id));
  }
  if (payload.template_id) params.set('template_id', payload.template_id);
  if (payload.mana_cost_min) params.set('mana_cost_min', payload.mana_cost_min);
  if (payload.mana_cost_max) params.set('mana_cost_max', payload.mana_cost_max);
  if (payload.attack_min) params.set('attack_min', payload.attack_min);
  if (payload.attack_max) params.set('attack_max', payload.attack_max);
  if (payload.health_min) params.set('health_min', payload.health_min);
  if (payload.health_max) params.set('health_max', payload.health_max);

  return params;
};

export const buildCardFilterApiPayload = (
  state: CardFilterSelectionState,
): CardFilterApiPayload => {
  const normalized = normalizeCardFilterSelectionState(state);
  const payload: CardFilterApiPayload = {};

  if (normalized.query) payload.q = normalized.query;
  if (normalized.lifecycleStatus !== 'active') payload.lifecycle_status = normalized.lifecycleStatus;
  if (normalized.keywordIds.length > 0) {
    payload.keyword_ids = normalized.keywordIds;
    payload.keyword_match = normalized.keywordMatch;
  }
  if (normalized.tagIds.length > 0) {
    payload.tag_ids = normalized.tagIds;
    payload.tag_match = normalized.tagMatch;
  }
  if (normalized.typeIds.length > 0) {
    payload.type_ids = normalized.typeIds;
    payload.type_match = normalized.typeMatch;
  }
  if (normalized.manaTypeSymbolIds.length > 0) {
    payload.mana_symbol_ids = normalized.manaTypeSymbolIds;
    payload.mana_symbol_match = normalized.manaSymbolMatch;
  }
  if (normalized.manaTypeSymbolExcludeIds.length > 0) {
    payload.mana_symbol_exclude_ids = normalized.manaTypeSymbolExcludeIds;
  }
  if (normalized.affinitySymbolIds.length > 0) {
    payload.affinity_symbol_ids = normalized.affinitySymbolIds;
    payload.affinity_symbol_match = normalized.affinitySymbolMatch;
  }
  if (normalized.affinitySymbolExcludeIds.length > 0) {
    payload.affinity_symbol_exclude_ids = normalized.affinitySymbolExcludeIds;
  }
  if (normalized.devotionSymbolIds.length > 0) {
    payload.devotion_symbol_ids = normalized.devotionSymbolIds;
    payload.devotion_symbol_match = normalized.devotionSymbolMatch;
  }
  if (normalized.devotionSymbolExcludeIds.length > 0) {
    payload.devotion_symbol_exclude_ids = normalized.devotionSymbolExcludeIds;
  }
  if (normalized.otherSymbolIds.length > 0) {
    payload.other_symbol_ids = normalized.otherSymbolIds;
    payload.other_symbol_match = normalized.otherSymbolMatch;
  }
  if (normalized.otherSymbolExcludeIds.length > 0) {
    payload.other_symbol_exclude_ids = normalized.otherSymbolExcludeIds;
  }
  if (normalized.templateId) payload.template_id = normalized.templateId;
  if (normalized.manaCostMin) payload.mana_cost_min = normalized.manaCostMin;
  if (normalized.manaCostMax) payload.mana_cost_max = normalized.manaCostMax;
  if (normalized.attackMin) payload.attack_min = normalized.attackMin;
  if (normalized.attackMax) payload.attack_max = normalized.attackMax;
  if (normalized.healthMin) payload.health_min = normalized.healthMin;
  if (normalized.healthMax) payload.health_max = normalized.healthMax;

  return payload;
};

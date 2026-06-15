import type { LocationQuery, LocationQueryRaw, LocationQueryValue } from 'vue-router';
import type { CardFiltersResponse, SymbolFilterOption } from '@/modules/card-detail/types';

export type DeckBrowseFilterState = {
  query: string;
  affinitySymbolMatch: 'any' | 'all';
  affinitySymbolKeys: string[];
  affinitySymbolExcludeKeys: string[];
};

export type DeckBrowseFilterSelectionState = {
  query: string;
  affinitySymbolMatch: 'any' | 'all';
  affinitySymbolIds: string[];
  affinitySymbolExcludeIds: string[];
};

export type DeckBrowseFilterCatalog = {
  affinitySymbols: SymbolFilterOption[];
};

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

const readQueryValues = (
  value: LocationQueryValue | LocationQueryValue[] | readonly LocationQueryValue[] | null | undefined,
): string[] => {
  if (Array.isArray(value)) {
    return value.filter((entry): entry is string => typeof entry === 'string');
  }
  return typeof value === 'string' ? [value] : [];
};

const resolveIdsFromKeys = (keys: string[], options: SymbolFilterOption[]): string[] => {
  const idByKey = new Map(options.map((option) => [option.key, option.id]));
  return keys.map((key) => idByKey.get(key)).filter((id): id is string => typeof id === 'string');
};

const resolveKeysFromIds = (ids: string[], options: SymbolFilterOption[]): string[] => {
  const keyById = new Map(options.map((option) => [option.id, option.key]));
  return ids.map((id) => keyById.get(id)).filter((key): key is string => typeof key === 'string');
};

export const createEmptyDeckBrowseFilterState = (): DeckBrowseFilterState => ({
  query: '',
  affinitySymbolMatch: 'any',
  affinitySymbolKeys: [],
  affinitySymbolExcludeKeys: [],
});

export const normalizeDeckBrowseFilterState = (state: DeckBrowseFilterState): DeckBrowseFilterState => ({
  query: normalizeStringValue(state.query),
  affinitySymbolMatch: state.affinitySymbolMatch === 'all' ? 'all' : 'any',
  affinitySymbolKeys: normalizeStringArray(state.affinitySymbolKeys),
  affinitySymbolExcludeKeys: normalizeStringArray(state.affinitySymbolExcludeKeys),
});

export const normalizeDeckBrowseFilterSelectionState = (
  state: DeckBrowseFilterSelectionState,
): DeckBrowseFilterSelectionState => ({
  query: normalizeStringValue(state.query),
  affinitySymbolMatch: state.affinitySymbolMatch === 'all' ? 'all' : 'any',
  affinitySymbolIds: normalizeStringArray(state.affinitySymbolIds),
  affinitySymbolExcludeIds: normalizeStringArray(state.affinitySymbolExcludeIds),
});

export const parseDeckBrowseFilterRouteQuery = (query: LocationQuery): DeckBrowseFilterState =>
  normalizeDeckBrowseFilterState({
    query: typeof query.q === 'string' ? query.q : '',
    affinitySymbolMatch: query.affinity_symbol_match === 'all' ? 'all' : 'any',
    affinitySymbolKeys: readQueryValues(query.affinity_symbol_keys),
    affinitySymbolExcludeKeys: readQueryValues(query.affinity_symbol_exclude_keys),
  });

export const buildDeckBrowseFilterRouteQuery = (state: DeckBrowseFilterState): LocationQueryRaw => {
  const normalized = normalizeDeckBrowseFilterState(state);
  const query: LocationQueryRaw = {};

  if (normalized.query) query.q = normalized.query;
  if (normalized.affinitySymbolMatch === 'all') query.affinity_symbol_match = 'all';
  if (normalized.affinitySymbolKeys.length > 0) query.affinity_symbol_keys = normalized.affinitySymbolKeys;
  if (normalized.affinitySymbolExcludeKeys.length > 0) {
    query.affinity_symbol_exclude_keys = normalized.affinitySymbolExcludeKeys;
  }

  return query;
};

export const buildDeckBrowseFilterRouteSearchParams = (state: DeckBrowseFilterState): URLSearchParams => {
  const params = new URLSearchParams();
  const query = buildDeckBrowseFilterRouteQuery(state);

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

export const getDeckBrowseFilterSignature = (state: DeckBrowseFilterState): string =>
  buildDeckBrowseFilterRouteSearchParams(state).toString();

export const sameDeckBrowseFilterState = (left: DeckBrowseFilterState, right: DeckBrowseFilterState): boolean =>
  getDeckBrowseFilterSignature(left) === getDeckBrowseFilterSignature(right);

export const createDeckBrowseFilterCatalog = (filters: CardFiltersResponse): DeckBrowseFilterCatalog => ({
  affinitySymbols: (filters.symbols ?? []).filter((row) => row.symbol_type === 'affinity'),
});

export const buildDeckBrowseFilterSelectionState = (
  state: DeckBrowseFilterState,
  catalog: DeckBrowseFilterCatalog,
): DeckBrowseFilterSelectionState =>
  normalizeDeckBrowseFilterSelectionState({
    query: state.query,
    affinitySymbolMatch: state.affinitySymbolMatch,
    affinitySymbolIds: resolveIdsFromKeys(state.affinitySymbolKeys, catalog.affinitySymbols),
    affinitySymbolExcludeIds: resolveIdsFromKeys(state.affinitySymbolExcludeKeys, catalog.affinitySymbols),
  });

export const buildDeckBrowseFilterStateFromSelection = (
  state: DeckBrowseFilterSelectionState,
  catalog: DeckBrowseFilterCatalog,
): DeckBrowseFilterState =>
  normalizeDeckBrowseFilterState({
    query: state.query,
    affinitySymbolMatch: state.affinitySymbolMatch,
    affinitySymbolKeys: resolveKeysFromIds(state.affinitySymbolIds, catalog.affinitySymbols),
    affinitySymbolExcludeKeys: resolveKeysFromIds(state.affinitySymbolExcludeIds, catalog.affinitySymbols),
  });

export const buildDeckBrowseFilterApiSearchParams = (
  state: DeckBrowseFilterSelectionState,
): URLSearchParams => {
  const normalized = normalizeDeckBrowseFilterSelectionState(state);
  const params = new URLSearchParams();

  if (normalized.query) params.set('q', normalized.query);
  if (normalized.affinitySymbolIds.length > 0) {
    normalized.affinitySymbolIds.forEach((id) => params.append('affinity_symbol_ids', id));
    params.set('affinity_symbol_match', normalized.affinitySymbolMatch);
  }
  if (normalized.affinitySymbolExcludeIds.length > 0) {
    normalized.affinitySymbolExcludeIds.forEach((id) => params.append('affinity_symbol_exclude_ids', id));
  }

  return params;
};

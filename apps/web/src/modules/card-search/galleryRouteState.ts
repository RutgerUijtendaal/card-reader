import type { LocationQuery, LocationQueryRaw, LocationQueryValue } from 'vue-router';

export type GalleryFilterState = {
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

export const createEmptyGalleryFilterState = (): GalleryFilterState => ({
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

export const normalizeGalleryFilterState = (state: GalleryFilterState): GalleryFilterState => ({
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

export const parseGalleryFilterState = (query: LocationQuery): GalleryFilterState =>
  normalizeGalleryFilterState({
    query: typeof query.q === 'string' ? query.q : '',
    manaCost: typeof query.mana_cost === 'string' ? query.mana_cost : '',
    templateId: typeof query.template_id === 'string' ? query.template_id : '',
    attackMin: typeof query.attack_min === 'string' ? query.attack_min : '',
    attackMax: typeof query.attack_max === 'string' ? query.attack_max : '',
    healthMin: typeof query.health_min === 'string' ? query.health_min : '',
    healthMax: typeof query.health_max === 'string' ? query.health_max : '',
    keywordIds: readQueryValues(query.keyword_ids),
    tagIds: readQueryValues(query.tag_ids),
    manaTypeSymbolIds: readQueryValues(query.mana_type_symbol_ids),
    affinitySymbolIds: readQueryValues(query.affinity_symbol_ids),
    devotionSymbolIds: readQueryValues(query.devotion_symbol_ids),
    otherSymbolIds: readQueryValues(query.other_symbol_ids),
    typeIds: readQueryValues(query.type_ids),
  });

export const buildGalleryRouteQuery = (state: GalleryFilterState): LocationQueryRaw => {
  const normalized = normalizeGalleryFilterState(state);
  const query: LocationQueryRaw = {};

  if (normalized.query) query.q = normalized.query;
  if (normalized.manaCost) query.mana_cost = normalized.manaCost;
  if (normalized.templateId) query.template_id = normalized.templateId;
  if (normalized.attackMin) query.attack_min = normalized.attackMin;
  if (normalized.attackMax) query.attack_max = normalized.attackMax;
  if (normalized.healthMin) query.health_min = normalized.healthMin;
  if (normalized.healthMax) query.health_max = normalized.healthMax;
  if (normalized.keywordIds.length > 0) query.keyword_ids = normalized.keywordIds;
  if (normalized.tagIds.length > 0) query.tag_ids = normalized.tagIds;
  if (normalized.manaTypeSymbolIds.length > 0) query.mana_type_symbol_ids = normalized.manaTypeSymbolIds;
  if (normalized.affinitySymbolIds.length > 0) query.affinity_symbol_ids = normalized.affinitySymbolIds;
  if (normalized.devotionSymbolIds.length > 0) query.devotion_symbol_ids = normalized.devotionSymbolIds;
  if (normalized.otherSymbolIds.length > 0) query.other_symbol_ids = normalized.otherSymbolIds;
  if (normalized.typeIds.length > 0) query.type_ids = normalized.typeIds;

  return query;
};

export const buildGalleryRouteSearchParams = (state: GalleryFilterState): URLSearchParams => {
  const params = new URLSearchParams();
  const query = buildGalleryRouteQuery(state);

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

export const buildGalleryApiSearchParams = (state: GalleryFilterState): URLSearchParams => {
  const normalized = normalizeGalleryFilterState(state);
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
  normalizeStringArray([
    ...normalized.manaTypeSymbolIds,
    ...normalized.affinitySymbolIds,
    ...normalized.devotionSymbolIds,
    ...normalized.otherSymbolIds,
  ]).forEach((id) => params.append('symbol_ids', id));
  normalized.typeIds.forEach((id) => params.append('type_ids', id));

  return params;
};

export const getGalleryFilterSignature = (state: GalleryFilterState): string =>
  buildGalleryRouteSearchParams(state).toString();

export const sameGalleryFilterState = (left: GalleryFilterState, right: GalleryFilterState): boolean =>
  getGalleryFilterSignature(left) === getGalleryFilterSignature(right);

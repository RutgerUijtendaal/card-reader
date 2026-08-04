import {
  DEFAULT_CARD_LIFECYCLE_FILTER,
  normalizeCardLifecycleFilterValue,
  type CardLifecycleFilterValue,
} from '@/domain/cards/utils/filters/cardLifecycle';

type FilterMatch = 'any' | 'all';

export type CardFilterState = {
  query: string;
  lifecycleStatus?: CardLifecycleFilterValue;
  keywordMatch: FilterMatch;
  tagMatch: FilterMatch;
  typeMatch: FilterMatch;
  manaSymbolMatch: FilterMatch;
  affinitySymbolMatch: FilterMatch;
  devotionSymbolMatch: FilterMatch;
  otherSymbolMatch: FilterMatch;
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
  typeExcludeKeys: string[];
};

export type CardFilterSelectionState = {
  query: string;
  lifecycleStatus?: CardLifecycleFilterValue;
  keywordMatch: FilterMatch;
  tagMatch: FilterMatch;
  typeMatch: FilterMatch;
  manaSymbolMatch: FilterMatch;
  affinitySymbolMatch: FilterMatch;
  devotionSymbolMatch: FilterMatch;
  otherSymbolMatch: FilterMatch;
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
  typeExcludeIds: string[];
};

export const createEmptyCardFilterState = (): CardFilterState => ({
  query: '',
  lifecycleStatus: DEFAULT_CARD_LIFECYCLE_FILTER,
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
  typeExcludeKeys: [],
});

export const createEmptyCardFilterSelectionState = (): CardFilterSelectionState => ({
  query: '',
  lifecycleStatus: DEFAULT_CARD_LIFECYCLE_FILTER,
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
  typeExcludeIds: [],
});

const normalizeStringValue = (value: string | number | null | undefined): string => {
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
  return value?.trim() ?? '';
};

const normalizeStringArray = (values: readonly string[]): string[] =>
  [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((left, right) =>
    left.localeCompare(right),
  );

const normalizeMatch = (value: FilterMatch): FilterMatch => (value === 'all' ? 'all' : 'any');

export const normalizeCardFilterState = (state: CardFilterState): CardFilterState => ({
  query: normalizeStringValue(state.query),
  lifecycleStatus: normalizeCardLifecycleFilterValue(state.lifecycleStatus),
  keywordMatch: normalizeMatch(state.keywordMatch),
  tagMatch: normalizeMatch(state.tagMatch),
  typeMatch: normalizeMatch(state.typeMatch),
  manaSymbolMatch: normalizeMatch(state.manaSymbolMatch),
  affinitySymbolMatch: normalizeMatch(state.affinitySymbolMatch),
  devotionSymbolMatch: normalizeMatch(state.devotionSymbolMatch),
  otherSymbolMatch: normalizeMatch(state.otherSymbolMatch),
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
  typeExcludeKeys: normalizeStringArray(state.typeExcludeKeys),
});

export const normalizeCardFilterSelectionState = (
  state: CardFilterSelectionState,
): CardFilterSelectionState => ({
  query: normalizeStringValue(state.query),
  lifecycleStatus: normalizeCardLifecycleFilterValue(state.lifecycleStatus),
  keywordMatch: normalizeMatch(state.keywordMatch),
  tagMatch: normalizeMatch(state.tagMatch),
  typeMatch: normalizeMatch(state.typeMatch),
  manaSymbolMatch: normalizeMatch(state.manaSymbolMatch),
  affinitySymbolMatch: normalizeMatch(state.affinitySymbolMatch),
  devotionSymbolMatch: normalizeMatch(state.devotionSymbolMatch),
  otherSymbolMatch: normalizeMatch(state.otherSymbolMatch),
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
  typeExcludeIds: normalizeStringArray(state.typeExcludeIds),
});

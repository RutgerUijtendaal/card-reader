import type { CardFiltersResponse, MetadataOption, SymbolFilterOption } from '@/domain/cards/types';
import {
  normalizeCardFilterSelectionState,
  normalizeCardFilterState,
  type CardFilterSelectionState,
  type CardFilterState,
} from '@/domain/cards/utils/filters/cardFilterState';
import { isManaFamily } from '@/domain/cards/manaFamilies';

export type CardFilterCatalog = {
  keywords: MetadataOption[];
  tags: MetadataOption[];
  types: MetadataOption[];
  manaFamilies: SymbolFilterOption[];
  affinitySymbols: SymbolFilterOption[];
  allAffinitySymbols: SymbolFilterOption[];
  devotionSymbols: SymbolFilterOption[];
  otherSymbols: SymbolFilterOption[];
  legacyManaFamilyBySymbolKey: Record<string, string>;
};

export const createCardFilterCatalog = (filters: CardFiltersResponse): CardFilterCatalog => {
  const legacyManaFamilyBySymbolKey: Record<string, string> = {};
  const manaFamilies = (filters.mana_families ?? []).map((family): SymbolFilterOption => {
    const displaySymbol = family.display_symbol ?? family.mana_symbol ?? family.affinity_symbol;
    [family.mana_symbol, family.affinity_symbol].forEach((symbol) => {
      if (symbol) legacyManaFamilyBySymbolKey[symbol.key] = family.key;
    });
    if (family.key === 'primal') legacyManaFamilyBySymbolKey['primla-affinity'] = family.key;
    return {
      id: family.key,
      key: family.key,
      label: family.label,
      symbol_type: 'mana_family',
      text_token: displaySymbol?.text_token ?? '',
      asset_url: displaySymbol?.asset_url ?? null,
    };
  });
  const pairedAffinityKeys = new Set(Object.keys(legacyManaFamilyBySymbolKey));
  const allAffinitySymbols = (filters.symbols ?? []).filter((row) => row.symbol_type === 'affinity');
  return {
    keywords: filters.keywords ?? [],
    tags: filters.tags ?? [],
    types: filters.types ?? [],
    manaFamilies,
    affinitySymbols: allAffinitySymbols.filter((row) => !pairedAffinityKeys.has(row.key)),
    allAffinitySymbols,
    devotionSymbols: (filters.symbols ?? []).filter((row) => row.symbol_type === 'devotion'),
    otherSymbols: (filters.symbols ?? []).filter(
      (row) => !['mana', 'devotion', 'affinity'].includes(row.symbol_type),
    ),
    legacyManaFamilyBySymbolKey,
  };
};

const retainAvailableKeys = (keys: string[], options: MetadataOption[]): string[] => {
  const availableKeys = new Set(options.map((option) => option.key));
  return keys.filter((key) => availableKeys.has(key));
};

export const reconcileCardFilterStateWithCatalog = (
  state: CardFilterState,
  catalog: CardFilterCatalog,
): CardFilterState => {
  const normalized = normalizeCardFilterState(state);
  const keywordKeys = retainAvailableKeys(normalized.keywordKeys, catalog.keywords);
  const tagKeys = retainAvailableKeys(normalized.tagKeys, catalog.tags);
  const typeKeys = retainAvailableKeys(normalized.typeKeys, catalog.types);
  const typeExcludeKeys = retainAvailableKeys(normalized.typeExcludeKeys, catalog.types);
  return normalizeCardFilterState({
    ...normalized,
    keywordKeys,
    keywordMatch: keywordKeys.length > 0 ? normalized.keywordMatch : 'any',
    tagKeys,
    tagMatch: tagKeys.length > 0 ? normalized.tagMatch : 'any',
    typeKeys,
    typeExcludeKeys,
    typeMatch: typeKeys.length > 0 || typeExcludeKeys.length > 0 ? normalized.typeMatch : 'any',
  });
};

const resolveIdsFromKeys = (keys: string[], options: MetadataOption[]): string[] => {
  const idByKey = new Map(options.map((option) => [option.key, option.id]));
  return keys.map((key) => idByKey.get(key)).filter((id): id is string => typeof id === 'string');
};

const resolveKeysFromIds = (ids: string[], options: MetadataOption[]): string[] => {
  const keyById = new Map(options.map((option) => [option.id, option.key]));
  return ids.map((id) => keyById.get(id)).filter((key): key is string => typeof key === 'string');
};

const resolveManaFamilyKeys = (
  keys: string[],
  legacyManaFamilyBySymbolKey: Readonly<Record<string, string>>,
): string[] => keys
  .map((key) => legacyManaFamilyBySymbolKey[key] ?? key)
  .filter(isManaFamily);

export const buildCardFilterSelectionState = (
  state: CardFilterState,
  catalog: CardFilterCatalog,
): CardFilterSelectionState => {
  const pairedAffinityKeys = state.affinitySymbolKeys.filter(
    (key) => catalog.legacyManaFamilyBySymbolKey[key],
  );
  const unmatchedAffinityKeys = state.affinitySymbolKeys.filter(
    (key) => !catalog.legacyManaFamilyBySymbolKey[key],
  );
  const translateAffinityPredicate = state.manaFamilyKeys.length === 0
    && pairedAffinityKeys.length > 0
    && unmatchedAffinityKeys.length === 0;

  return normalizeCardFilterSelectionState({
    query: state.query,
    lifecycleStatus: state.lifecycleStatus,
    cardPool: state.cardPool,
    cardRoleMatch: state.cardRoleMatch,
    cardRoleIds: state.cardRoleKeys,
    cardRoleExcludeIds: state.cardRoleExcludeKeys,
    cardFactionMatch: state.cardFactionMatch,
    cardFactionIds: state.cardFactionKeys,
    cardFactionExcludeIds: state.cardFactionExcludeKeys,
    keywordMatch: state.keywordMatch,
    tagMatch: state.tagMatch,
    typeMatch: state.typeMatch,
    manaFamilyMatch: translateAffinityPredicate ? state.affinitySymbolMatch : state.manaFamilyMatch,
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
    manaFamilyIds: resolveManaFamilyKeys(
      [
        ...state.manaFamilyKeys,
        ...(translateAffinityPredicate ? pairedAffinityKeys : []),
      ],
      catalog.legacyManaFamilyBySymbolKey,
    ),
    manaFamilyExcludeIds: resolveManaFamilyKeys(
      [...state.manaFamilyExcludeKeys, ...state.affinitySymbolExcludeKeys],
      catalog.legacyManaFamilyBySymbolKey,
    ),
    affinitySymbolIds: resolveIdsFromKeys(
      translateAffinityPredicate ? [] : state.affinitySymbolKeys,
      catalog.allAffinitySymbols,
    ),
    affinitySymbolExcludeIds: resolveIdsFromKeys(
      state.affinitySymbolExcludeKeys.filter(
        (key) => !catalog.legacyManaFamilyBySymbolKey[key],
      ),
      catalog.affinitySymbols,
    ),
    devotionSymbolIds: resolveIdsFromKeys(state.devotionSymbolKeys, catalog.devotionSymbols),
    devotionSymbolExcludeIds: resolveIdsFromKeys(state.devotionSymbolExcludeKeys, catalog.devotionSymbols),
    otherSymbolIds: resolveIdsFromKeys(state.otherSymbolKeys, catalog.otherSymbols),
    otherSymbolExcludeIds: resolveIdsFromKeys(state.otherSymbolExcludeKeys, catalog.otherSymbols),
    typeIds: resolveIdsFromKeys(state.typeKeys, catalog.types),
    typeExcludeIds: resolveIdsFromKeys(state.typeExcludeKeys, catalog.types),
  });
};

export const buildCardFilterStateFromSelection = (
  state: CardFilterSelectionState,
  catalog: CardFilterCatalog,
): CardFilterState =>
  normalizeCardFilterState({
    query: state.query,
    lifecycleStatus: state.lifecycleStatus,
    cardPool: state.cardPool,
    cardRoleMatch: state.cardRoleMatch,
    cardRoleKeys: state.cardRoleIds,
    cardRoleExcludeKeys: state.cardRoleExcludeIds,
    cardFactionMatch: state.cardFactionMatch,
    cardFactionKeys: state.cardFactionIds,
    cardFactionExcludeKeys: state.cardFactionExcludeIds,
    keywordMatch: state.keywordMatch,
    tagMatch: state.tagMatch,
    typeMatch: state.typeMatch,
    manaFamilyMatch: state.manaFamilyMatch,
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
    manaFamilyKeys: state.manaFamilyIds.filter(isManaFamily),
    manaFamilyExcludeKeys: state.manaFamilyExcludeIds.filter(isManaFamily),
    affinitySymbolKeys: resolveKeysFromIds(state.affinitySymbolIds, catalog.allAffinitySymbols),
    affinitySymbolExcludeKeys: resolveKeysFromIds(state.affinitySymbolExcludeIds, catalog.allAffinitySymbols),
    devotionSymbolKeys: resolveKeysFromIds(state.devotionSymbolIds, catalog.devotionSymbols),
    devotionSymbolExcludeKeys: resolveKeysFromIds(state.devotionSymbolExcludeIds, catalog.devotionSymbols),
    otherSymbolKeys: resolveKeysFromIds(state.otherSymbolIds, catalog.otherSymbols),
    otherSymbolExcludeKeys: resolveKeysFromIds(state.otherSymbolExcludeIds, catalog.otherSymbols),
    typeKeys: resolveKeysFromIds(state.typeIds, catalog.types),
    typeExcludeKeys: resolveKeysFromIds(state.typeExcludeIds, catalog.types),
  });
